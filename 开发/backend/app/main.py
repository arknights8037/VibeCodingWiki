from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import admin, auth, courses, projects, reviews, skills, wiki
from app.config import settings
from app.database import get_session, init_database
from app.mcp_server import mcp, mcp_http_app
from app.models import PublicationStatus, SkillPackage
from app.services.skills import build_skill_archive


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_database()
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="VibeCodingWiki REST API and MCP service",
    lifespan=lifespan,
)
settings.data_dir.joinpath("media").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.data_dir / "media")), name="media")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-CSRF-Token",
        "MCP-Protocol-Version",
        "Mcp-Method",
        "Mcp-Name",
    ],
    expose_headers=["Mcp-Session-Id"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


api_prefix = "/api/v1"
for router in (
    auth.router,
    courses.router,
    wiki.router,
    projects.router,
    reviews.router,
    skills.router,
    admin.router,
):
    app.include_router(router, prefix=api_prefix)


async def published_skill(slug: str, version: str, session: AsyncSession) -> SkillPackage:
    skill = await session.scalar(
        select(SkillPackage).where(
            SkillPackage.slug == slug,
            SkillPackage.version == version,
            SkillPackage.status == PublicationStatus.published,
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return skill


@app.get("/skills/{slug}/{version}/SKILL.md", response_class=PlainTextResponse)
async def raw_skill(slug: str, version: str, session: AsyncSession = Depends(get_session)) -> str:
    return (await published_skill(slug, version, session)).skill_md


@app.get("/skills/{slug}/{version}/download.zip")
async def download_skill(slug: str, version: str, session: AsyncSession = Depends(get_session)):
    skill = await published_skill(slug, version, session)
    archive = build_skill_archive(skill.skill_md, skill.files_json)
    return StreamingResponse(
        BytesIO(archive),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{slug}-{version}.zip"'},
    )


# The MCP ASGI app is mounted last because Mount("/") catches every unmatched route.
app.mount("/", mcp_http_app)

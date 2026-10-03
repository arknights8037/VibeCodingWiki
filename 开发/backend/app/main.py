import base64
import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import admin, auth, content_categories, courses, projects, reviews, skills, wiki
from app.config import settings
from app.database import SessionLocal, engine, get_session, init_database
from app.mcp_server import (
    admin_mcp,
    admin_mcp_http_app,
    authenticate_admin_token,
    mcp,
    mcp_http_app,
)
from app.models import MCPSettings, PublicationStatus, SkillPackage
from app.services.skills import build_skill_archive


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_database()
    try:
        async with mcp.session_manager.run(), admin_mcp.session_manager.run():
            yield
    finally:
        await engine.dispose()


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
        "Authorization",
        "X-CSRF-Token",
        "MCP-Protocol-Version",
        "Mcp-Method",
        "Mcp-Name",
    ],
    expose_headers=["Mcp-Session-Id"],
)


@app.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await session.execute(text("SELECT id FROM users LIMIT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}


api_prefix = "/api/v1"
for router in (
    auth.router,
    courses.router,
    wiki.router,
    content_categories.router,
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
async def raw_skill(slug: str, version: str, session: AsyncSession = Depends(get_session)):
    return PlainTextResponse((await published_skill(slug, version, session)).skill_md,
                             headers={"Access-Control-Allow-Origin": "*"})


@app.get("/skills/{slug}/{version}/download.zip")
async def download_skill(slug: str, version: str, session: AsyncSession = Depends(get_session)):
    skill = await published_skill(slug, version, session)
    archive = build_skill_archive(skill.skill_md, skill.files_json)
    return StreamingResponse(
        BytesIO(archive),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{slug}-{version}.zip"', "Access-Control-Allow-Origin": "*"},
    )


@app.get("/skills/{slug}/{version}/{file_path:path}")
async def skill_resource(slug: str, version: str, file_path: str, session: AsyncSession = Depends(get_session)):
    skill = await published_skill(slug, version, session)
    encoded = json.loads(skill.files_json).get(file_path)
    if encoded is None:
        raise HTTPException(404, "Skill 文件不存在")
    return Response(base64.b64decode(encoded), media_type="application/octet-stream", headers={
        "Access-Control-Allow-Origin": "*", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "attachment",
    })


# The MCP ASGI app is mounted last because Mount("/") catches every unmatched route.
async def public_mcp_app(scope, receive, send):
    """Apply the administrator's public MCP enable/auth settings."""
    if scope["type"] != "http":
        await mcp_http_app(scope, receive, send)
        return
    # Starlette's catch-all mount also receives the slashless form. Normalize
    # it so both `/mcp/admin` and `/mcp/admin/` are valid MCP endpoints.
    if scope.get("path") == "/mcp/admin":
        admin_scope = {**scope, "path": "/", "raw_path": b"/"}
        await admin_mcp_app(admin_scope, receive, send)
        return
    async with SessionLocal() as session:
        row = await session.get(MCPSettings, 1)
    if row and not row.enabled:
        await JSONResponse({"error": "MCP 服务已停用"}, status_code=503)(scope, receive, send)
        return
    if row and row.auth_enabled:
        headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
        scheme, _, token = headers.get("authorization", "").partition(" ")
        digest = hashlib.sha256(token.strip().encode()).hexdigest() if token else ""
        if scheme.lower() != "bearer" or not row.auth_token_hash or not hmac.compare_digest(
            digest, row.auth_token_hash
        ):
            await JSONResponse({"error": "MCP 凭证无效"}, status_code=401)(scope, receive, send)
            return
    await mcp_http_app(scope, receive, send)


async def admin_mcp_app(scope, receive, send):
    """The write-capable MCP endpoint is always protected by a Bearer token."""
    if scope["type"] != "http":
        await admin_mcp_http_app(scope, receive, send)
        return
    headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
    scheme, _, token = headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        await JSONResponse({"error": "管理员 MCP 凭证无效"}, status_code=401)(scope, receive, send)
        return
    async with SessionLocal() as session:
        row = await session.get(MCPSettings, 1)
        if row and not row.enabled:
            await JSONResponse({"error": "MCP 服务已停用"}, status_code=503)(scope, receive, send)
            return
        admin = await authenticate_admin_token(session, token)
    if not admin:
        await JSONResponse({"error": "管理员 MCP 凭证无效"}, status_code=401)(scope, receive, send)
        return
    if scope.get("path") == "":
        scope = {**scope, "path": "/", "raw_path": b"/"}
    await admin_mcp_http_app(scope, receive, send)


# Mount the protected write endpoint before the public catch-all MCP mount.
app.mount("/mcp/admin", admin_mcp_app)
app.mount("/", public_mcp_app)

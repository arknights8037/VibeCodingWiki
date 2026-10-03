import hashlib
import hmac
import json
from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import (
    Course,
    Lesson,
    MCPSettings,
    ProjectSubmission,
    PublicationStatus,
    Role,
    SkillPackage,
    User,
    WikiArticle,
)
from app.services.block_content import normalize_content_json
from app.services.search import search_wiki_articles

mcp = MCPServer("VibeCodingWiki")
admin_mcp = MCPServer("VibeCodingWiki Admin")


@mcp.tool()
async def search_wiki(query: str, category: str | None = None, limit: int = 10) -> list[dict]:
    """Search published VibeCodingWiki articles."""
    async with SessionLocal() as session:
        items, _ = await search_wiki_articles(
            session, q=query, category=category, page_size=max(1, min(limit, 20))
        )
        return [{"slug": item.slug, "title": item.title, "summary": item.summary} for item in items]


@mcp.tool()
async def get_wiki_article(slug: str) -> dict:
    """Read one published Wiki article by slug."""
    async with SessionLocal() as session:
        article = await session.scalar(
            select(WikiArticle).where(
                WikiArticle.slug == slug, WikiArticle.status == PublicationStatus.published
            )
        )
        if not article:
            return {"error": "article_not_found"}
        return {
            "slug": article.slug,
            "title": article.title,
            "summary": article.summary,
            "body_markdown": article.body_markdown,
            "content_json": article.content_json,
        }


@mcp.tool()
async def list_courses() -> list[dict]:
    """List published learning-path modules."""
    async with SessionLocal() as session:
        courses = await session.scalars(
            select(Course)
            .where(Course.status == PublicationStatus.published)
            .order_by(Course.order_index)
        )
        return [
            {"slug": item.slug, "title": item.title, "summary": item.summary} for item in courses
        ]


@mcp.tool()
async def get_lesson(slug: str) -> dict:
    """Read one published lesson by slug."""
    async with SessionLocal() as session:
        lesson = await session.scalar(
            select(Lesson).where(Lesson.slug == slug, Lesson.status == PublicationStatus.published)
        )
        if not lesson:
            return {"error": "lesson_not_found"}
        return {
            "slug": lesson.slug,
            "title": lesson.title,
            "objective": lesson.objective,
            "body_markdown": lesson.body_markdown,
            "content_json": lesson.content_json,
            "practice": lesson.practice,
            "completion_criteria": lesson.completion_criteria,
        }


@mcp.tool()
async def list_projects(limit: int = 20) -> list[dict]:
    """List published open-source projects."""
    async with SessionLocal() as session:
        projects = await session.scalars(
            select(ProjectSubmission)
            .where(ProjectSubmission.status == PublicationStatus.published)
            .order_by(ProjectSubmission.is_featured.desc(), ProjectSubmission.published_at.desc())
            .limit(max(1, min(limit, 50)))
        )
        return [
            {
                "slug": item.slug,
                "name": item.name,
                "summary": item.summary,
                "repository_url": item.repository_url,
                "tech_stack": json.loads(item.tech_stack or "[]"),
            }
            for item in projects
        ]


@mcp.tool()
async def list_skills() -> list[dict]:
    """List published Agent Skill packages."""
    async with SessionLocal() as session:
        skills = await session.scalars(
            select(SkillPackage)
            .where(SkillPackage.status == PublicationStatus.published)
            .order_by(SkillPackage.name)
        )
        return [
            {
                "slug": item.slug,
                "name": item.name,
                "summary": item.summary,
                "version": item.version,
                "sha256": item.sha256,
            }
            for item in skills
        ]


async def authenticate_admin_token(session, token: str) -> User | None:
    """Return the active admin represented by a global or personal MCP token."""
    digest = hashlib.sha256(token.strip().encode()).hexdigest()
    settings_row = await session.get(MCPSettings, 1)
    if settings_row and settings_row.auth_token_hash and hmac.compare_digest(
        digest, settings_row.auth_token_hash
    ):
        return await session.scalar(
            select(User)
            .where(User.role == Role.admin, User.is_active.is_(True))
            .order_by(User.id)
        )
    return await session.scalar(
        select(User).where(
            User.role == Role.admin,
            User.is_active.is_(True),
            User.mcp_token_hash == digest,
        )
    )


async def _require_admin_credential(ctx: Context, session) -> User:
    """Authenticate the configured administrator MCP credential.

    The admin endpoint is always credentialed, even when public MCP
    authentication is disabled. Global admin tokens and personal MCP tokens
    belonging to active administrators are accepted. Tokens are stored as
    SHA-256 digests and are never returned by the service.
    """
    headers = {key.lower(): value for key, value in (ctx.headers or {}).items()}
    authorization = headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise PermissionError("管理员 MCP 工具需要 Authorization: Bearer <token>")

    admin = await authenticate_admin_token(session, token)
    if not admin:
        raise PermissionError("管理员 MCP 凭证无效或尚未配置")
    return admin


@admin_mcp.tool()
async def update_wiki_article(
    slug: str,
    title: str | None = None,
    summary: str | None = None,
    body_markdown: str | None = None,
    content_json: str | None = None,
    status: Literal["draft", "published"] | None = None,
    ctx: Context | None = None,
) -> dict:
    """Update an existing Wiki article using the administrator MCP credential."""
    if ctx is None:
        raise PermissionError("管理员 MCP 工具需要 HTTP 凭证")
    async with SessionLocal() as session:
        admin = await _require_admin_credential(ctx, session)
        article = await session.scalar(
            select(WikiArticle)
            .where(WikiArticle.slug == slug)
            .options(selectinload(WikiArticle.category), selectinload(WikiArticle.tags))
        )
        if not article:
            raise ValueError("词条不存在")
        if title is not None:
            if not 2 <= len(title.strip()) <= 180:
                raise ValueError("标题长度必须为 2–180 个字符")
            article.title = title.strip()
        if summary is not None:
            if not 10 <= len(summary.strip()) <= 500:
                raise ValueError("摘要长度必须为 10–500 个字符")
            article.summary = summary.strip()
        if body_markdown is not None:
            if len(body_markdown.strip()) < 20 or len(body_markdown) > 50000:
                raise ValueError("正文长度必须为 20–50000 个字符")
            article.body_markdown = body_markdown
            article.content_json = normalize_content_json(content_json, body_markdown)
        elif content_json is not None:
            article.content_json = content_json
        if status is not None:
            article.status = PublicationStatus(status)
        article.version += 1

        from app.api.admin import write_audit

        await write_audit(
            session,
            admin,
            "wiki.update.mcp",
            "wiki",
            str(article.id),
            {"slug": article.slug, "status": str(article.status), "version": article.version},
        )
        await session.commit()
        return {
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "summary": article.summary,
            "status": article.status.value,
            "version": article.version,
        }


@admin_mcp.tool()
async def update_lesson(
    slug: str,
    title: str | None = None,
    objective: str | None = None,
    body_markdown: str | None = None,
    content_json: str | None = None,
    practice: str | None = None,
    completion_criteria: str | None = None,
    status: Literal["draft", "published", "archived"] | None = None,
    ctx: Context | None = None,
) -> dict:
    """Update an existing lesson using the administrator MCP credential."""
    if ctx is None:
        raise PermissionError("管理员 MCP 工具需要 HTTP 凭证")
    async with SessionLocal() as session:
        admin = await _require_admin_credential(ctx, session)
        lesson = await session.scalar(select(Lesson).where(Lesson.slug == slug))
        if not lesson:
            raise ValueError("课文不存在")
        if title is not None:
            if not 1 <= len(title.strip()) <= 180:
                raise ValueError("标题长度必须为 1–180 个字符")
            lesson.title = title.strip()
        if objective is not None:
            lesson.objective = objective
        if body_markdown is not None:
            lesson.body_markdown = body_markdown
            lesson.content_json = normalize_content_json(content_json, body_markdown)
        elif content_json is not None:
            lesson.content_json = content_json
        if practice is not None:
            lesson.practice = practice
        if completion_criteria is not None:
            lesson.completion_criteria = completion_criteria
        if status is not None:
            lesson.status = PublicationStatus(status)

        from app.api.admin import write_audit

        await write_audit(
            session,
            admin,
            "lesson.update.mcp",
            "lesson",
            str(lesson.id),
            {"slug": lesson.slug, "status": str(lesson.status)},
        )
        await session.commit()
        return {
            "id": lesson.id,
            "slug": lesson.slug,
            "title": lesson.title,
            "status": lesson.status.value,
        }


@admin_mcp.tool()
async def update_course(
    slug: str,
    title: str | None = None,
    summary: str | None = None,
    prerequisites: str | None = None,
    status: Literal["draft", "published", "archived"] | None = None,
    ctx: Context | None = None,
) -> dict:
    """Update course metadata using the administrator MCP credential."""
    if ctx is None:
        raise PermissionError("管理员 MCP 工具需要 HTTP 凭证")
    async with SessionLocal() as session:
        admin = await _require_admin_credential(ctx, session)
        course = await session.scalar(select(Course).where(Course.slug == slug))
        if not course:
            raise ValueError("课程不存在")
        if title is not None:
            if not 1 <= len(title.strip()) <= 160:
                raise ValueError("标题长度必须为 1–160 个字符")
            course.title = title.strip()
        if summary is not None:
            course.summary = summary
        if prerequisites is not None:
            course.prerequisites = prerequisites
        if status is not None:
            course.status = PublicationStatus(status)

        from app.api.admin import write_audit

        await write_audit(
            session,
            admin,
            "course.update.mcp",
            "course",
            str(course.id),
            {"slug": course.slug, "status": str(course.status)},
        )
        await session.commit()
        return {
            "id": course.id,
            "slug": course.slug,
            "title": course.title,
            "status": course.status.value,
        }


@mcp.resource("wiki://articles/{slug}")
async def wiki_resource(slug: str) -> str:
    """Return a published Wiki article as Markdown."""
    result = await get_wiki_article(slug)
    return result.get("body_markdown", "Article not found")


@mcp.resource("course://lessons/{slug}")
async def lesson_resource(slug: str) -> str:
    """Return a published lesson as Markdown."""
    result = await get_lesson(slug)
    return result.get("body_markdown", "Lesson not found")


mcp_http_app = mcp.streamable_http_app()
admin_mcp_http_app = admin_mcp.streamable_http_app(streamable_http_path="/")

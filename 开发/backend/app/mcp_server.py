import hashlib
import hmac
import json
from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.mcp_catalog import ADMIN_MCP_TOOLS, PUBLIC_MCP_TOOLS
from app.models import (
    Category,
    Course,
    Difficulty,
    Lesson,
    MCPSettings,
    MCPToolSetting,
    ProjectSubmission,
    PublicationStatus,
    Role,
    SkillPackage,
    User,
    WikiArticle,
)
from app.services.block_content import normalize_content_json
from app.services.search import search_wiki_articles


class ConfigurableMCPServer(MCPServer):
    """MCPServer that applies the administrator's per-tool exposure switches."""

    def __init__(self, *args, managed_tool_names: set[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.managed_tool_names = frozenset(managed_tool_names)

    async def _enabled_tool_names(self) -> set[str]:
        async with SessionLocal() as session:
            rows = await session.scalars(
                select(MCPToolSetting).where(MCPToolSetting.name.in_(self.managed_tool_names))
            )
            disabled = {row.name for row in rows if not row.enabled}
        # A newly added tool remains available until its settings row is created by
        # the admin settings endpoint. This keeps startup and migrations backwards compatible.
        return set(self.managed_tool_names) - disabled

    async def list_tools(self):
        enabled = await self._enabled_tool_names()
        tools = await super().list_tools()
        return [tool for tool in tools if tool.name not in self.managed_tool_names or tool.name in enabled]

    async def call_tool(self, name, arguments, context=None):
        if name in self.managed_tool_names and name not in await self._enabled_tool_names():
            raise ToolError(f"MCP 工具已停用：{name}")
        return await super().call_tool(name, arguments, context)


mcp = ConfigurableMCPServer("VibeCodingWiki", managed_tool_names=set(PUBLIC_MCP_TOOLS))
admin_mcp = ConfigurableMCPServer("VibeCodingWiki Admin", managed_tool_names=set(ADMIN_MCP_TOOLS))


async def _admin_session(ctx: Context | None):
    """Open a session and authenticate an administrator MCP request."""
    if ctx is None:
        raise PermissionError("管理员 MCP 工具需要 HTTP 凭证")
    session = SessionLocal()
    try:
        admin = await _require_admin_credential(ctx, session)
        return session, admin
    except Exception:
        await session.close()
        raise


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
async def list_wiki_categories() -> list[dict]:
    """List Wiki categories containing published articles."""
    async with SessionLocal() as session:
        categories = await session.scalars(
            select(Category)
            .where(Category.articles.any(WikiArticle.status == PublicationStatus.published))
            .order_by(Category.order_index, Category.name)
        )
        return [
            {
                "id": item.id,
                "slug": item.slug,
                "name": item.name,
                "parent_id": item.parent_id,
                "order_index": item.order_index,
            }
            for item in categories
        ]


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
    content_json: str | dict | None = None,
    status: Literal["draft", "published"] | None = None,
    ctx: Context | None = None,
) -> dict:
    """Update an existing Wiki article using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
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
            article.content_json = normalize_content_json(content_json, article.body_markdown)
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
async def create_wiki_article(
    slug: str,
    title: str,
    summary: str,
    body_markdown: str,
    category: str,
    category_id: int | None = None,
    tags: list[str] | None = None,
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner",
    order_index: int = 0,
    status: Literal["draft", "published"] = "draft",
    content_json: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Create a Wiki article using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
        if await session.scalar(select(WikiArticle.id).where(WikiArticle.slug == slug)):
            raise ValueError("词条标识已存在")
        if not 2 <= len(title.strip()) <= 180 or not 10 <= len(summary.strip()) <= 500:
            raise ValueError("标题或摘要长度不符合要求")
        if len(body_markdown.strip()) < 20 or len(body_markdown) > 50000:
            raise ValueError("正文长度必须为 20–50000 个字符")
        if order_index < 0:
            raise ValueError("排序值不能为负数")
        from app.api.admin import resolve_category_and_tags, write_audit

        category_obj, tag_objs = await resolve_category_and_tags(
            session, category, tags or [], category_id
        )
        article = WikiArticle(
            slug=slug,
            title=title.strip(),
            summary=summary.strip(),
            body_markdown=body_markdown,
            content_json=normalize_content_json(content_json, body_markdown),
            difficulty=Difficulty(difficulty),
            status=PublicationStatus(status),
            category=category_obj,
            tags=tag_objs,
            order_index=order_index,
        )
        session.add(article)
        await session.flush()
        await write_audit(session, admin, "wiki.create.mcp", "wiki", str(article.id), {"slug": slug})
        await session.commit()
        return {"id": article.id, "slug": article.slug, "title": article.title, "status": article.status.value}


@admin_mcp.tool()
async def delete_wiki_article(slug: str, ctx: Context | None = None) -> dict:
    """Delete a Wiki article using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
        article = await session.scalar(select(WikiArticle).where(WikiArticle.slug == slug))
        if not article:
            raise ValueError("词条不存在")
        article_id = article.id
        await session.delete(article)
        from app.api.admin import write_audit

        await write_audit(session, admin, "wiki.delete.mcp", "wiki", str(article_id), {"slug": slug})
        await session.commit()
        return {"deleted": True, "id": article_id, "slug": slug}


@admin_mcp.tool()
async def move_wiki_article(slug: str, offset: Literal[-1, 1], ctx: Context | None = None) -> dict:
    """Move a Wiki article within its category using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
        article = await session.scalar(select(WikiArticle).where(WikiArticle.slug == slug))
        if not article:
            raise ValueError("词条不存在")
        siblings = list(await session.scalars(select(WikiArticle).where(WikiArticle.category_id == article.category_id).order_by(WikiArticle.order_index, WikiArticle.id)))
        index = next(i for i, item in enumerate(siblings) if item.id == article.id)
        target = index + offset
        if target < 0 or target >= len(siblings):
            raise ValueError("已在该分类边界")
        siblings[index], siblings[target] = siblings[target], siblings[index]
        for position, item in enumerate(siblings):
            item.order_index = position
        from app.api.admin import write_audit

        await write_audit(session, admin, "wiki.move.mcp", "wiki", str(article.id), {"offset": offset})
        await session.commit()
        return {"slug": slug, "order_index": article.order_index}


@admin_mcp.tool()
async def create_wiki_category(
    slug: str,
    name: str,
    parent_id: int | None = None,
    order_index: int = 0,
    ctx: Context | None = None,
) -> dict:
    """Create a Wiki category using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
        if await session.scalar(select(Category.id).where((Category.slug == slug) | (Category.name == name))):
            raise ValueError("分类标识或名称已存在")
        if parent_id is not None and not await session.get(Category, parent_id):
            raise ValueError("父级分类不存在")
        category = Category(slug=slug, name=name.strip(), parent_id=parent_id, order_index=max(0, order_index))
        session.add(category)
        await session.flush()
        from app.api.admin import write_audit

        await write_audit(session, admin, "wiki.category.create.mcp", "wiki_category", str(category.id), {"slug": slug})
        await session.commit()
        return {"id": category.id, "slug": category.slug, "name": category.name, "parent_id": category.parent_id, "order_index": category.order_index}


@admin_mcp.tool()
async def update_wiki_category(
    category_id: int,
    slug: str,
    name: str,
    parent_id: int | None = None,
    order_index: int = 0,
    ctx: Context | None = None,
) -> dict:
    """Update a Wiki category using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
        category = await session.get(Category, category_id)
        if not category:
            raise ValueError("分类不存在")
        if parent_id == category_id or (parent_id is not None and not await session.get(Category, parent_id)):
            raise ValueError("父级分类无效")
        duplicate = await session.scalar(select(Category.id).where(((Category.slug == slug) | (Category.name == name)), Category.id != category_id))
        if duplicate:
            raise ValueError("分类标识或名称已存在")
        category.slug, category.name, category.parent_id, category.order_index = slug, name.strip(), parent_id, max(0, order_index)
        from app.api.admin import write_audit

        await write_audit(session, admin, "wiki.category.update.mcp", "wiki_category", str(category_id), {"slug": slug})
        await session.commit()
        return {"id": category.id, "slug": category.slug, "name": category.name, "parent_id": category.parent_id, "order_index": category.order_index}


@admin_mcp.tool()
async def delete_wiki_category(category_id: int, ctx: Context | None = None) -> dict:
    """Delete a Wiki category and its descendant articles using the administrator MCP credential."""
    session, admin = await _admin_session(ctx)
    async with session:
        category = await session.get(Category, category_id)
        if not category:
            raise ValueError("分类不存在")
        categories = list(await session.scalars(select(Category)))
        children = {}
        for item in categories:
            children.setdefault(item.parent_id, []).append(item)
        descendants, pending = [], [category]
        while pending:
            item = pending.pop()
            descendants.append(item)
            pending.extend(children.get(item.id, []))
        ids = [item.id for item in descendants]
        article_ids = list(await session.scalars(select(WikiArticle.id).where(WikiArticle.category_id.in_(ids))))
        if article_ids:
            await session.execute(WikiArticle.__table__.delete().where(WikiArticle.id.in_(article_ids)))
        await session.execute(Category.__table__.delete().where(Category.id.in_(ids)))
        from app.api.admin import write_audit

        await write_audit(session, admin, "wiki.category.delete.mcp", "wiki_category", str(category_id), {"category_ids": ids, "article_ids": article_ids})
        await session.commit()
        return {"deleted": True, "category_ids": ids, "article_ids": article_ids}


@admin_mcp.tool()
async def update_lesson(
    slug: str,
    title: str | None = None,
    objective: str | None = None,
    body_markdown: str | None = None,
    content_json: str | dict | None = None,
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
            lesson.content_json = normalize_content_json(content_json, lesson.body_markdown)
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


@admin_mcp.tool()
async def replace_course_directory(
    directory: list[dict],
    archive_existing: bool = True,
    ctx: Context | None = None,
) -> dict:
    """Replace the course directory with empty draft courses and lessons.

    Each directory item must contain ``slug``, ``title``, ``difficulty`` and a
    ``lessons`` list. Each lesson must contain ``slug`` and ``title``. This
    deliberately writes directory metadata only; all lesson content fields are
    cleared so editors can fill them later.
    """
    session, admin = await _admin_session(ctx)
    allowed_difficulties = {"beginner", "intermediate", "advanced"}
    async with session:
        if not directory:
            raise ValueError("课程目录不能为空")
        course_slugs: set[str] = set()
        lesson_slugs: set[str] = set()
        for item in directory:
            if not isinstance(item, dict):
                raise ValueError("课程目录项格式无效")
            slug = str(item.get("slug", "")).strip()
            title = str(item.get("title", "")).strip()
            difficulty = str(item.get("difficulty", "")).strip()
            lessons = item.get("lessons")
            if not slug or not title or difficulty not in allowed_difficulties or not isinstance(lessons, list):
                raise ValueError("课程目录项必须包含 slug、title、difficulty 和 lessons")
            if slug in course_slugs:
                raise ValueError(f"课程标识重复：{slug}")
            course_slugs.add(slug)
            for lesson_item in lessons:
                if not isinstance(lesson_item, dict):
                    raise ValueError("课文目录项格式无效")
                lesson_slug = str(lesson_item.get("slug", "")).strip()
                lesson_title = str(lesson_item.get("title", "")).strip()
                if not lesson_slug or not lesson_title:
                    raise ValueError("课文目录项必须包含 slug 和 title")
                if lesson_slug in lesson_slugs:
                    raise ValueError(f"课文标识重复：{lesson_slug}")
                lesson_slugs.add(lesson_slug)

        if archive_existing:
            await session.execute(
                Lesson.__table__.update().values(status=PublicationStatus.archived)
            )
            await session.execute(
                Course.__table__.update().values(status=PublicationStatus.archived)
            )

        for course_order, item in enumerate(directory, start=1):
            course = await session.scalar(select(Course).where(Course.slug == item["slug"]))
            if course is None:
                course = Course(
                    slug=item["slug"],
                    title=item["title"].strip(),
                    summary="",
                    prerequisites="无",
                )
                session.add(course)
                await session.flush()
            course.title = item["title"].strip()
            course.summary = ""
            course.prerequisites = "无"
            course.difficulty = Difficulty(item["difficulty"])
            course.order_index = course_order
            course.status = PublicationStatus.draft
            course.is_standalone = False
            course.directory_collapsible = True

            for lesson_order, lesson_item in enumerate(item["lessons"], start=1):
                lesson = await session.scalar(
                    select(Lesson).where(Lesson.slug == lesson_item["slug"])
                )
                if lesson is None:
                    lesson = Lesson(course_id=course.id, slug=lesson_item["slug"])
                    session.add(lesson)
                lesson.course_id = course.id
                lesson.title = lesson_item["title"].strip()
                lesson.objective = ""
                lesson.body_markdown = ""
                lesson.content_json = ""
                lesson.practice = ""
                lesson.completion_criteria = ""
                lesson.estimated_minutes = 30
                lesson.order_index = lesson_order
                lesson.status = PublicationStatus.draft

        from app.api.admin import write_audit

        await write_audit(
            session,
            admin,
            "course.directory.replace.mcp",
            "course_directory",
            "all",
            {"course_count": len(directory), "lesson_count": len(lesson_slugs)},
        )
        await session.commit()
        return {
            "course_count": len(directory),
            "lesson_count": len(lesson_slugs),
            "archived_existing": archive_existing,
            "status": "draft",
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

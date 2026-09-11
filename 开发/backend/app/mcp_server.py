import json

from mcp.server import MCPServer
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Course,
    Lesson,
    ProjectSubmission,
    PublicationStatus,
    SkillPackage,
    WikiArticle,
)
from app.services.search import search_wiki_articles

mcp = MCPServer("VibeCodingWiki")


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

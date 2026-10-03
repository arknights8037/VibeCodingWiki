import asyncio
import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.config import settings
from app.database import SessionLocal, init_database
from app.models import (
    Category,
    ContentCategory,
    Course,
    Difficulty,
    Lesson,
    ProjectSubmission,
    PublicationStatus,
    Role,
    SkillPackage,
    Tag,
    User,
    WikiArticle,
)
from app.security import hash_password
from app.seed_data import COURSES, RETIRED_COURSE_SLUGS, RETIRED_WIKI_SLUGS, WIKI
from app.services.block_content import markdown_to_content
from app.services.lesson_content import with_legacy_cards
from app.services.skills import build_skill_archive


async def seed() -> None:
    await init_database()
    async with SessionLocal() as session:
        # Keep a stable default for legacy API clients that do not send a
        # content category yet. Administrators can add more categories later.
        for kind, slug, name in (
            ("project", "general", "综合项目"),
            ("skill", "general", "通用技能"),
        ):
            category = await session.scalar(
                select(ContentCategory).where(
                    ContentCategory.kind == kind,
                    ContentCategory.slug == slug,
                )
            )
            if not category:
                session.add(ContentCategory(kind=kind, slug=slug, name=name, order_index=0))
        await session.flush()
        # Keep historical learning progress while removing retired teaching content
        # from public pages, search results, and MCP resources.
        retired_courses = select(Course.id).where(Course.slug.in_(RETIRED_COURSE_SLUGS))
        await session.execute(
            update(Lesson)
            .where(Lesson.course_id.in_(retired_courses))
            .values(status=PublicationStatus.archived)
        )
        await session.execute(
            update(Course)
            .where(Course.slug.in_(RETIRED_COURSE_SLUGS))
            .values(status=PublicationStatus.archived)
        )
        await session.execute(
            update(WikiArticle)
            .where(
                WikiArticle.slug.in_(RETIRED_WIKI_SLUGS),
                WikiArticle.status != PublicationStatus.archived,
            )
            .values(status=PublicationStatus.archived)
        )
        admin = await session.scalar(select(User).where(User.email == settings.admin_email.lower()))
        if not admin:
            admin = User(
                email=settings.admin_email.lower(),
                display_name="系统管理员",
                password_hash=hash_password(settings.admin_password),
                role=Role.admin,
            )
            session.add(admin)
            await session.flush()

        for order_index, item in enumerate(COURSES, start=1):
            course = await session.scalar(select(Course).where(Course.slug == item["slug"]))
            if not course:
                course = Course(
                    slug=item["slug"],
                    title=item["title"],
                    summary=item["summary"],
                    prerequisites=item["prerequisites"],
                    difficulty=Difficulty(item["difficulty"]),
                    order_index=order_index,
                    status=PublicationStatus.published,
                )
                session.add(course)
                await session.flush()
            else:
                course.title = item["title"]
                course.summary = item["summary"]
                course.prerequisites = item["prerequisites"]
                course.difficulty = Difficulty(item["difficulty"])
                course.order_index = order_index
            for lesson_order, lesson_item in enumerate(item["lessons"], start=1):
                body_markdown = with_legacy_cards(
                    lesson_item["body"],
                    lesson_item["objective"],
                    lesson_item["practice"],
                    lesson_item["criteria"],
                )
                existing_lesson = await session.scalar(
                    select(Lesson).where(Lesson.slug == lesson_item["slug"])
                )
                if not existing_lesson:
                    existing_lesson = Lesson(course_id=course.id, slug=lesson_item["slug"])
                    session.add(existing_lesson)
                existing_lesson.course_id = course.id
                existing_lesson.title = lesson_item["title"]
                existing_lesson.objective = lesson_item["objective"]
                existing_lesson.body_markdown = body_markdown
                existing_lesson.content_json = markdown_to_content(body_markdown)
                existing_lesson.practice = lesson_item["practice"]
                existing_lesson.completion_criteria = lesson_item["criteria"]
                existing_lesson.estimated_minutes = 40
                existing_lesson.order_index = lesson_order
                existing_lesson.status = PublicationStatus.published

        category_cache: dict[str, Category] = {}
        tag_cache: dict[str, Tag] = {}
        for slug, title, category_name, summary, body, difficulty, tag_names in WIKI:
            if await session.scalar(select(WikiArticle).where(WikiArticle.slug == slug)):
                continue
            category_slug = category_name.lower().replace(" ", "-")
            category = category_cache.get(category_slug) or await session.scalar(
                select(Category).where(Category.slug == category_slug)
            )
            if not category:
                category = Category(slug=category_slug, name=category_name)
                session.add(category)
                await session.flush()
            category_cache[category_slug] = category
            tags: list[Tag] = []
            for tag_name in tag_names:
                tag = tag_cache.get(tag_name) or await session.scalar(
                    select(Tag).where(Tag.slug == tag_name)
                )
                if not tag:
                    tag = Tag(slug=tag_name, name=tag_name)
                    session.add(tag)
                    await session.flush()
                tag_cache[tag_name] = tag
                tags.append(tag)
            body_markdown = f"# {title}\n\n{body}\n\n## 使用建议\n\n结合课程示例运行和验证，不要只记住定义。"
            session.add(
                WikiArticle(
                    slug=slug,
                    title=title,
                    summary=summary,
                    body_markdown=body_markdown,
                    content_json=markdown_to_content(body_markdown),
                    difficulty=Difficulty(difficulty),
                    category=category,
                    tags=tags,
                    status=PublicationStatus.published,
                    published_at=datetime.now(UTC),
                )
            )

        skill_md = """---
name: safe-wiki-research
description: Search VibeCodingWiki for published concepts and return a concise study note with source links. Use when learning Vibe Coding concepts.
license: MIT
compatibility: Requires network access to the VibeCodingWiki public API
---

# Safe Wiki Research

1. Search the VibeCodingWiki public API with the user's terms.
2. Read only published entries and preserve their titles and URLs.
3. Summarize the answer in plain language.
4. State when no relevant entry is found. Do not invent an entry.
"""
        if not await session.scalar(
            select(SkillPackage).where(
                SkillPackage.slug == "safe-wiki-research", SkillPackage.version == "1.0.0"
            )
        ):
            session.add(
                SkillPackage(
                    slug="safe-wiki-research",
                    name="safe-wiki-research",
                    summary="查询已发布 Wiki 并生成带来源的学习笔记。",
                    version="1.0.0",
                    license_name="MIT",
                    compatibility="需要访问 VibeCodingWiki 公共 API",
                    skill_md=skill_md,
                    files_json="{}",
                    sha256=hashlib.sha256(build_skill_archive(skill_md, "{}")).hexdigest(),
                    status=PublicationStatus.published,
                )
            )

        if not await session.scalar(
            select(ProjectSubmission).where(ProjectSubmission.slug == "vibecodingwiki")
        ):
            session.add(
                ProjectSubmission(
                    owner_id=admin.id,
                    name="VibeCodingWiki",
                    slug="vibecodingwiki",
                    summary="面向零基础学习者的课程、Wiki、项目分享和开放标准服务。",
                    description_markdown="# VibeCodingWiki\n\n本项目演示课程、知识检索、投稿审核、MCP 和 Agent Skills 分发。",
                    repository_url="https://github.com/your-account/VibeCodingWiki",
                    demo_url=None,
                    license_name="MIT",
                    tech_stack=json.dumps(
                        ["Vue 3", "TypeScript", "FastAPI", "SQLite"], ensure_ascii=False
                    ),
                    status=PublicationStatus.published,
                    is_featured=True,
                    submitted_at=datetime.now(UTC),
                    published_at=datetime.now(UTC),
                )
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())

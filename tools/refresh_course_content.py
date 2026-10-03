"""Refresh the versioned public course prose in an existing development DB.

This command is intentionally explicit: normal application startup never
overwrites editorial content.  Back up the SQLite file before running it when
the database contains manual course edits.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Imports below resolve the application package from this repository.
# ruff: noqa: E402

BACKEND = Path(__file__).resolve().parents[1] / "开发" / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, init_database
from app.models import Course, Difficulty, Lesson, PublicationStatus
from app.seed_data import COURSES
from app.services.block_content import markdown_to_content
from app.services.lesson_content import with_legacy_cards


async def refresh() -> int:
    await init_database()
    changed = 0
    async with SessionLocal() as session:
        for order_index, item in enumerate(COURSES, start=1):
            course = await session.scalar(select(Course).where(Course.slug == item["slug"]))
            if not course:
                continue
            course.title = item["title"]
            course.summary = item["summary"]
            course.prerequisites = item["prerequisites"]
            course.order_index = order_index
            course.difficulty = Difficulty(item["difficulty"])
            existing_lessons = list(
                (
                    await session.scalars(
                        select(Lesson)
                        .where(Lesson.course_id == course.id)
                        .order_by(Lesson.order_index, Lesson.id)
                    )
                ).all()
            )
            by_slug = {lesson.slug: lesson for lesson in existing_lessons}
            used_ids: set[int] = set()
            for lesson_order, lesson_item in enumerate(item["lessons"], start=1):
                lesson = by_slug.get(lesson_item["slug"])
                # Preserve the original lesson row (and its progress) for the
                # first redesigned article when migrating the old one-lesson shape.
                if lesson is None and lesson_order == 1:
                    lesson = next(
                        (candidate for candidate in existing_lessons if candidate.id not in used_ids),
                        None,
                    )
                    if lesson is not None:
                        lesson.slug = lesson_item["slug"]
                if lesson is None:
                    lesson = Lesson(course_id=course.id, slug=lesson_item["slug"])
                    session.add(lesson)
                body = with_legacy_cards(
                    lesson_item["body"],
                    lesson_item["objective"],
                    lesson_item["practice"],
                    lesson_item["criteria"],
                )
                lesson.title = lesson_item["title"]
                lesson.body_markdown = body
                lesson.content_json = markdown_to_content(body)
                lesson.objective = lesson_item["objective"]
                lesson.practice = lesson_item["practice"]
                lesson.completion_criteria = lesson_item["criteria"]
                lesson.estimated_minutes = 40
                lesson.order_index = lesson_order
                lesson.status = PublicationStatus.published
                if lesson.id is not None:
                    used_ids.add(lesson.id)
                changed += 1
            for lesson in existing_lessons:
                if lesson.id not in used_ids:
                    lesson.status = PublicationStatus.archived
        await session.commit()
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        help="Optional SQLite file path; defaults to VCW_DATABASE_URL/data/vibecodingwiki.db.",
    )
    args = parser.parse_args()
    if args.database:
        settings.database_url = f"sqlite+aiosqlite:///{args.database.resolve().as_posix()}"
        settings.data_dir = args.database.resolve().parent
    count = asyncio.run(refresh())
    print(f"refreshed {count} course lessons")


if __name__ == "__main__":
    main()

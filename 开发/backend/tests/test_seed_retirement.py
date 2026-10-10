from sqlalchemy import select

from app.database import SessionLocal
from app.mcp_server import get_lesson, get_wiki_article
from app.models import (
    Category,
    Course,
    Lesson,
    LessonProgress,
    PublicationStatus,
    User,
    WikiArticle,
)
from app.seed import seed


async def test_existing_technical_content_is_retired_without_losing_progress(client):
    async with SessionLocal() as session:
        course = Course(
            slug="vue-typescript",
            title="旧前端课程",
            summary="旧内容",
            order_index=5,
            status=PublicationStatus.published,
        )
        custom = Course(
            slug="custom-course",
            title="自定义课程",
            summary="保留内容",
            order_index=10,
            status=PublicationStatus.published,
        )
        category = Category(slug="frontend", name="前端")
        session.add_all([course, custom, category])
        await session.flush()
        lesson = Lesson(
            course_id=course.id,
            slug="vue-typescript-lesson",
            title="旧前端课文",
            objective="学习前端",
            body_markdown="旧课文",
            practice="旧练习",
            completion_criteria="旧标准",
            status=PublicationStatus.published,
        )
        session.add(lesson)
        session.add(
            WikiArticle(
                slug="vue-3",
                title="Vue 3",
                summary="前端框架",
                body_markdown="旧术语",
                category_id=category.id,
                status=PublicationStatus.published,
            )
        )
        await session.flush()
        user_id = await session.scalar(select(User.id).limit(1))
        session.add(LessonProgress(user_id=user_id, lesson_id=lesson.id))
        # Existing installations numbered the quality module seventh.
        quality = await session.scalar(
            select(Course).where(Course.slug == "testing-security-review")
        )
        quality.order_index = 7
        await session.commit()

    await seed()
    await seed()

    courses = (await client.get("/api/v1/courses")).json()
    assert "vue-typescript" not in {course["slug"] for course in courses}
    assert "custom-course" in {course["slug"] for course in courses}
    assert [course["order_index"] for course in courses] == list(range(1, 11))
    assert (await client.get("/api/v1/courses/vue-typescript")).status_code == 404
    assert (await client.get("/api/v1/wiki/vue-3")).status_code == 404
    assert (await client.get("/api/v1/wiki", params={"q": "Vue"})).json()["total"] == 0
    categories = (await client.get("/api/v1/wiki/categories")).json()
    assert "frontend" not in {category["slug"] for category in categories}
    assert await get_lesson("vue-typescript-lesson") == {"error": "lesson_not_found"}
    assert await get_wiki_article("vue-3") == {"error": "article_not_found"}

    async with SessionLocal() as session:
        progress = await session.scalar(select(LessonProgress))
        assert progress is not None
        lesson = await session.get(Lesson, progress.lesson_id)
        assert lesson.status == PublicationStatus.archived

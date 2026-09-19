import pytest
from sqlalchemy import select

from app.database import SessionLocal, init_database
from app.models import Lesson


@pytest.mark.asyncio
async def test_legacy_teaching_fields_migrate_once_and_keep_fenced_examples(client):
    async with SessionLocal() as session:
        lesson = await session.scalar(select(Lesson).order_by(Lesson.id))
        lesson.body_markdown = '# Original body'
        lesson.objective = 'Understand the result'
        lesson.practice = '```python\nprint(1)\n```'
        lesson.completion_criteria = 'Verify once'
        lesson_id = lesson.id
        await session.commit()
    await init_database()
    async with SessionLocal() as session:
        lesson = await session.get(Lesson, lesson_id)
        migrated = lesson.body_markdown
        assert migrated.startswith('# Original body')
        assert '````card' in migrated and '```python\nprint(1)\n```' in migrated
        assert not lesson.objective and not lesson.practice and not lesson.completion_criteria
    await init_database()
    async with SessionLocal() as session:
        assert (await session.get(Lesson, lesson_id)).body_markdown == migrated

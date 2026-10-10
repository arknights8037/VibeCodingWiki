import json

import pytest
from sqlalchemy import select

from app.database import SessionLocal, init_database
from app.models import Lesson
from app.services.block_content import markdown_to_content
from app.services.lesson_content import deduplicate_teaching_cards, with_legacy_cards


def test_legacy_cards_are_idempotent_and_preserve_different_content_and_examples():
    body = '# Manual body\n\n````markdown\n```card\n## 学习目标\n\nExample only\n```\n````\n'
    migrated = with_legacy_cards(body, 'Understand', '```python\nprint(1)\n```', 'Verify')
    assert with_legacy_cards(migrated, 'Understand', '```python\nprint(1)\n```', 'Verify') == migrated
    assert migrated.startswith(body.rstrip())
    different = '\n\n```card\n## 学习目标\n\nDifferent objective\n```'
    assert deduplicate_teaching_cards(migrated + different) == migrated + different


@pytest.mark.asyncio
async def test_seed_then_repeated_startup_keeps_one_teaching_card_set(client):
    await init_database()
    await init_database()
    courses = (await client.get('/api/v1/courses')).json()
    for course in courses:
        for lesson in course['lessons']:
            for title in ('学习目标', '实践任务', '完成标准'):
                assert lesson['body_markdown'].count(f'## {title}') == 1
            assert not lesson['objective'] and not lesson['practice'] and not lesson['completion_criteria']


@pytest.mark.asyncio
async def test_startup_repairs_existing_duplicates_and_preserves_manual_content_and_ids(client):
    cards = with_legacy_cards('', 'Understand', 'Practice', 'Verify')
    body = '# Manually edited body\n\nKeep this text.\n\n' + cards + '\n\n' + cards
    document = json.loads(markdown_to_content(body))
    document['content'][1]['attrs']['manual_setting'] = 'preserve'
    first_card_id = document['content'][2]['attrs']['id']
    async with SessionLocal() as session:
        lesson = await session.scalar(select(Lesson).order_by(Lesson.id))
        lesson.body_markdown = body
        lesson.content_json = json.dumps(document)
        lesson.objective = lesson.practice = lesson.completion_criteria = ''
        lesson_id = lesson.id
        await session.commit()
    await init_database()
    async with SessionLocal() as session:
        lesson = await session.get(Lesson, lesson_id)
        repaired = lesson.body_markdown
        assert repaired == '# Manually edited body\n\nKeep this text.\n\n' + cards
        content = json.loads(lesson.content_json)['content']
        assert len(content) == 5
        assert content[1]['attrs']['manual_setting'] == 'preserve'
        assert content[2]['attrs']['id'] == first_card_id
        repaired_json = lesson.content_json
    await init_database()
    async with SessionLocal() as session:
        lesson = await session.get(Lesson, lesson_id)
        assert lesson.body_markdown == repaired
        assert lesson.content_json == repaired_json


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

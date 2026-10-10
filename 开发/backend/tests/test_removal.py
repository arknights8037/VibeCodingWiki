import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Lesson, LessonProgress, ReviewEvent
from tests.test_admin import login_admin


@pytest.mark.asyncio
async def test_remove_courses_and_lessons_cascades_progress_and_checks_access(client):
    path = '/api/v1/admin/courses/1'
    assert (await client.delete(path)).status_code in (401, 403)
    headers = await login_admin(client)
    courses = (await client.get('/api/v1/admin/courses')).json()
    course = courses[0]
    lesson = course['lessons'][0]
    await client.post(f"/api/v1/courses/lessons/{lesson['slug']}/complete", headers=headers)
    assert (await client.delete(f"/api/v1/admin/lessons/{lesson['id']}")).status_code == 403
    assert (await client.delete(f"/api/v1/admin/lessons/{lesson['id']}", headers=headers)).status_code == 200
    async with SessionLocal() as session:
        assert await session.get(Lesson, lesson['id']) is None
        assert await session.scalar(select(LessonProgress).where(LessonProgress.lesson_id == lesson['id'])) is None
    remaining = (await client.get(f"/api/v1/courses/{course['slug']}")).json()['lessons']
    for remaining_lesson in remaining:
        assert (await client.delete(
            f"/api/v1/admin/lessons/{remaining_lesson['id']}", headers=headers
        )).status_code == 200
    assert (await client.get(f"/api/v1/courses/{course['slug']}")).json()['lessons'] == []
    other = courses[1]
    lesson = other['lessons'][0]
    await client.post(f"/api/v1/courses/lessons/{lesson['slug']}/complete", headers=headers)
    assert (await client.delete(f"/api/v1/admin/courses/{other['id']}", headers=headers)).status_code == 200
    assert (await client.get(f"/api/v1/courses/{other['slug']}")).status_code == 404
    async with SessionLocal() as session:
        assert await session.get(Lesson, lesson['id']) is None
        assert await session.scalar(select(LessonProgress).where(LessonProgress.lesson_id == lesson['id'])) is None
    assert (await client.delete(f"/api/v1/admin/courses/{other['id']}", headers=headers)).status_code == 404
    audit = (await client.get('/api/v1/admin/audit-logs')).json()
    assert {'courses.delete', 'lessons.delete'} <= {item['action'] for item in audit}


@pytest.mark.asyncio
async def test_remove_wiki_project_skill_and_users(client):
    headers = await login_admin(client)
    wiki = (await client.get('/api/v1/admin/wiki')).json()[0]
    assert (await client.delete(f"/api/v1/admin/wiki/{wiki['id']}", headers=headers)).status_code == 200
    assert (await client.get(f"/api/v1/wiki/{wiki['slug']}")).status_code == 404
    search = (await client.get('/api/v1/wiki', params={'q': wiki['title']})).json()
    assert not any(item['id'] == wiki['id'] for item in search['items'])
    skill = (await client.get('/api/v1/admin/skills')).json()[0]
    assert (await client.delete(f"/api/v1/admin/skills/{skill['id']}", headers=headers)).status_code == 200
    assert (await client.get(f"/skills/{skill['slug']}/{skill['version']}/download.zip")).status_code == 404
    project = (await client.get('/api/v1/projects')).json()[0]
    assert (await client.delete(f"/api/v1/admin/projects/{project['id']}", headers=headers)).status_code == 200
    assert (await client.get(f"/api/v1/projects/{project['slug']}")).status_code == 404
    admin = (await client.get('/api/v1/auth/me')).json()
    assert (await client.delete(f"/api/v1/admin/users/{admin['id']}", headers=headers)).status_code == 409
    credentials = dict(email='remove-user@example.com', display_name='Remove user', password='StrongPassword123!')
    user = (await client.post('/api/v1/auth/register', json=credentials)).json()
    async with SessionLocal() as session:
        session.add(AuditLog(actor_id=user['id'], action='test.action', target_type='test', target_id='1'))
        await session.commit()
    assert (await client.delete(f"/api/v1/admin/users/{user['id']}", headers=headers)).status_code == 200
    assert (await client.post('/api/v1/auth/login', json=credentials)).status_code == 401
    async with SessionLocal() as session:
        log = await session.scalar(select(AuditLog).where(AuditLog.action == 'test.action'))
        assert log is not None and log.actor_id is None


@pytest.mark.asyncio
async def test_remove_denied_to_non_admin_and_preserves_reviewer_history(client):
    credentials = dict(email='reviewer-delete@example.com', display_name='Reviewer', password='StrongPassword123!')
    user = (await client.post('/api/v1/auth/register', json=credentials)).json()
    headers = await login_admin(client)
    await client.patch(f"/api/v1/admin/users/{user['id']}/role", json={'role': 'reviewer'}, headers=headers)
    async with SessionLocal() as session:
        session.add(ReviewEvent(entity_type='project', entity_id=999, action='approve', reviewer_id=user['id']))
        await session.commit()
    assert (await client.delete(f"/api/v1/admin/users/{user['id']}", headers=headers)).status_code == 409
    await client.post('/api/v1/auth/login', json=credentials)
    for resource in ['courses', 'lessons', 'wiki', 'projects', 'skills', 'users']:
        assert (await client.delete(f'/api/v1/admin/{resource}/1', headers={'X-CSRF-Token': client.cookies['csrf_token']})).status_code == 403

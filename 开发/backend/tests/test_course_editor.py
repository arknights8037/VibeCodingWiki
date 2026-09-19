import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import LessonProgress
from tests.test_admin import login_admin


@pytest.mark.asyncio
async def test_course_editor_visibility_progress_validation_and_permissions(client):
    assert (await client.get('/api/v1/admin/courses')).status_code == 401
    headers = await login_admin(client)
    course = (await client.get('/api/v1/admin/courses')).json()[0]
    lesson = course['lessons'][0]
    await client.post(f"/api/v1/courses/lessons/{lesson['slug']}/complete", headers=headers)
    course['directory_collapsible'] = False
    course['lessons'].append(dict(slug='unpublished-lesson', title='隐藏草稿', status='draft', order_index=99))
    path = f"/api/v1/admin/courses/{course['id']}"
    assert (await client.put(path, json=course)).status_code == 403
    response = await client.put(path, json=course, headers=headers)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated['lessons'][0]['id'] == lesson['id']
    async with SessionLocal() as session:
        assert await session.scalar(select(LessonProgress).where(LessonProgress.lesson_id == lesson['id']))
    public = (await client.get(f"/api/v1/courses/{course['slug']}")).json()
    assert public['directory_collapsible'] is False
    assert 'unpublished-lesson' not in [item['slug'] for item in public['lessons']]
    catalog = (await client.get('/api/v1/courses')).json()
    assert not any(item['slug'] == 'unpublished-lesson' for c in catalog for item in c['lessons'])
    updated['lessons'][-1]['status'] = 'published'
    updated['lessons'][-1]['body_markdown'] = '# 已更新正文\n\n**加粗内容**'
    assert (await client.put(path, json=updated, headers=headers)).status_code == 200
    assert len((await client.get(f"/api/v1/courses/{course['slug']}")).json()['lessons']) == len(updated['lessons'])
    updated['lessons'] = []
    assert (await client.put(path, json=updated, headers=headers)).status_code == 422
    new = dict(slug='new-category', title='新增分类', lessons=[], status='draft')
    created = await client.post('/api/v1/admin/courses', json=new, headers=headers)
    assert created.status_code == 200, created.text
    assert (await client.get('/api/v1/courses/new-category')).status_code == 404
    assert (await client.post('/api/v1/admin/courses', json=new, headers=headers)).status_code == 409
    await client.post('/api/v1/auth/register', json=dict(email='course-user@example.com', display_name='课程用户', password='StrongPassword123!'))
    await client.post('/api/v1/auth/login', json=dict(email='course-user@example.com', password='StrongPassword123!'))
    assert (await client.get('/api/v1/admin/courses')).status_code == 403
    assert (await client.put(path, json=course, headers={'X-CSRF-Token': client.cookies['csrf_token']})).status_code == 403

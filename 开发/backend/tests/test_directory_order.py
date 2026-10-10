import pytest

from tests.test_admin import login_admin


@pytest.mark.asyncio
async def test_standalone_and_atomic_directory_moves(client):
    headers = await login_admin(client)
    payload = dict(title='Root', slug='root-entry', difficulty='advanced', is_standalone=True,
                   lessons=[dict(title='Root entry', slug='root-entry', status='published', body_markdown='# Root')])
    response = await client.post('/api/v1/admin/courses', json=payload, headers=headers)
    assert response.status_code == 200, response.text
    root = response.json()
    assert root['status'] == 'published' and root['title'] == 'Root entry'
    assert (await client.get('/api/v1/courses/root-entry')).json()['is_standalone']
    category = (await client.post('/api/v1/admin/courses', headers=headers, json=dict(title='Category', slug='move-category', difficulty='advanced', order_index=99, lessons=[dict(title='A', slug='move-a', order_index=0),dict(title='B', slug='move-b', order_index=1)]))).json()
    path = f"/api/v1/admin/courses/{category['id']}/move"
    assert (await client.post(path, json={'offset': -1})).status_code == 403
    before = [c['id'] for c in (await client.get('/api/v1/admin/courses')).json() if c['difficulty'] == 'advanced']
    assert (await client.post(path, json={'offset': -1}, headers=headers)).status_code == 200
    after = [c['id'] for c in (await client.get('/api/v1/admin/courses')).json() if c['difficulty'] == 'advanced']
    assert after.index(category['id']) == before.index(category['id']) - 1
    while (await client.post(path, json={'offset': -1}, headers=headers)).status_code == 200:
        pass
    assert (await client.post(path, json={'offset': -1}, headers=headers)).status_code == 409
    lesson_path = f"/api/v1/admin/lessons/{category['lessons'][1]['id']}/move"
    assert (await client.post(lesson_path, json={'offset': -1}, headers=headers)).status_code == 200
    rows = (await client.get('/api/v1/admin/courses')).json()
    updated = next(c for c in rows if c['id'] == category['id'])
    assert [lesson['slug'] for lesson in updated['lessons']] == ['move-b', 'move-a']
    payload['lessons'] = []
    assert (await client.post('/api/v1/admin/courses', json=payload, headers=headers)).status_code == 422
    assert (await client.delete(f"/api/v1/admin/lessons/{root['lessons'][0]['id']}", headers=headers)).status_code == 200
    assert (await client.get('/api/v1/courses/root-entry')).status_code == 404

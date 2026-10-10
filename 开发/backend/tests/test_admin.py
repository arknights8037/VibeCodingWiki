import pytest


async def login_admin(client):
    await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
    return {'X-CSRF-Token': client.cookies['csrf_token']}


@pytest.mark.asyncio
async def test_wiki_editor_lifecycle(client):
    headers = await login_admin(client)
    payload = dict(slug='editor-test', title='后台测试', summary='后台编辑测试摘要至少十个字符', body_markdown='后台编辑正文包含足够多的字符用于验证保存发布流程。', category='工程工具', tags=['Git', 'git'], status='draft')
    created = await client.post('/api/v1/admin/wiki', json=payload, headers=headers)
    assert created.status_code == 201
    article_id = created.json()['id']
    assert len(created.json()['tags']) == 1
    assert (await client.get('/api/v1/wiki/editor-test')).status_code == 404
    assert any(a['id'] == article_id for a in (await client.get('/api/v1/admin/wiki')).json())
    payload['status'] = 'published'
    assert (await client.put(f'/api/v1/admin/wiki/{article_id}', json=payload, headers=headers)).status_code == 200
    assert (await client.get('/api/v1/wiki/editor-test')).status_code == 200
    payload['slug'] = 'git'
    assert (await client.put(f'/api/v1/admin/wiki/{article_id}', json=payload, headers=headers)).status_code == 409
    payload['status'] = 'pending_review'
    assert (await client.put(f'/api/v1/admin/wiki/{article_id}', json=payload, headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_disable_account_revokes_refresh_and_blocks_self_disable(client):
    user = {'email': 'disable@example.com', 'display_name': '账号测试', 'password': 'StrongPassword123!'}
    user_id = (await client.post('/api/v1/auth/register', json=user)).json()['id']
    await client.post('/api/v1/auth/login', json=user)
    old_refresh = client.cookies['refresh_token']
    headers = await login_admin(client)
    admin_id = (await client.get('/api/v1/auth/me')).json()['id']
    assert (await client.patch(f'/api/v1/admin/users/{admin_id}/status', json={'is_active': False}, headers=headers)).status_code == 409
    assert (await client.patch(f'/api/v1/admin/users/{user_id}/status', json={'is_active': False})).status_code == 403
    assert (await client.patch(f'/api/v1/admin/users/{user_id}/status', json={'is_active': False}, headers=headers)).status_code == 200
    assert (await client.post('/api/v1/auth/login', json=user)).status_code == 401
    await client.patch(f'/api/v1/admin/users/{user_id}/status', json={'is_active': True}, headers=headers)
    client.cookies.clear()
    client.cookies.set('refresh_token', old_refresh)
    client.cookies.set('csrf_token', 'test')
    assert (await client.post('/api/v1/auth/refresh', headers={'X-CSRF-Token': 'test'})).status_code == 401


@pytest.mark.asyncio
async def test_admin_can_change_own_password(client):
    headers = await login_admin(client)
    response = await client.post('/api/v1/auth/password', json={
        'current_password': 'AdminPassword123!',
        'new_password': 'ChangedAdmin456!',
    }, headers=headers)
    assert response.status_code == 200
    assert (await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})).status_code == 401
    assert (await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'ChangedAdmin456!'})).status_code == 200


@pytest.mark.asyncio
async def test_wiki_category_delete_cascades_after_confirmation(client):
    headers = await login_admin(client)
    parent = (await client.post('/api/v1/admin/wiki/categories', json={
        'slug': 'cascade-parent', 'name': '级联父分类', 'parent_id': None, 'order_index': 0,
    }, headers=headers)).json()
    child = (await client.post('/api/v1/admin/wiki/categories', json={
        'slug': 'cascade-child', 'name': '级联子分类', 'parent_id': parent['id'], 'order_index': 0,
    }, headers=headers)).json()
    article = await client.post('/api/v1/admin/wiki', json={
        'slug': 'cascade-article', 'title': '级联词条', 'summary': '级联删除测试摘要足够长',
        'body_markdown': '级联删除测试正文足够长，删除分类时应一并移除。', 'category': child['name'],
        'category_id': child['id'], 'tags': [], 'status': 'draft',
    }, headers=headers)
    assert article.status_code == 201
    assert (await client.delete(f"/api/v1/admin/wiki/categories/{parent['id']}", headers=headers)).status_code == 200
    assert not any(item['id'] == parent['id'] for item in (await client.get('/api/v1/admin/wiki/categories')).json())
    assert not any(item['id'] == article.json()['id'] for item in (await client.get('/api/v1/admin/wiki')).json())


@pytest.mark.asyncio
async def test_skill_visibility_and_admin_permissions(client):
    assert (await client.get('/api/v1/admin/wiki')).status_code == 401
    headers = await login_admin(client)
    skill = (await client.get('/api/v1/admin/skills')).json()[0]
    path = f"/api/v1/admin/skills/{skill['id']}/status"
    assert (await client.patch(path, json={'status': 'draft'}, headers=headers)).status_code == 200
    assert (await client.get('/api/v1/skills')).json() == []
    assert (await client.get(f"/skills/{skill['slug']}/{skill['version']}/download.zip")).status_code == 404
    assert (await client.patch(path, json={'status': 'published'}, headers=headers)).status_code == 200
    assert len((await client.get('/api/v1/skills')).json()) == 1
    assert any(a['action'] == 'skill.status.update' for a in (await client.get('/api/v1/admin/audit-logs')).json())

@pytest.mark.asyncio
async def test_published_project_management(client):
    user = {'email': 'author@example.com', 'display_name': '项目作者', 'password': 'StrongPassword123!'}
    await client.post('/api/v1/auth/register', json=user)
    await client.post('/api/v1/auth/login', json=user)
    headers = {'X-CSRF-Token': client.cookies['csrf_token']}
    payload = dict(name='测试项目', slug='feature-project', summary='这是用于项目审核测试的摘要说明', description_markdown='这是一段完整的项目说明用于验证审核和推荐以及下架流程。', repository_url='https://example.com/repo')
    project_id = (await client.post('/api/v1/projects', json=payload, headers=headers)).json()['id']
    await client.post(f'/api/v1/projects/{project_id}/submit', headers=headers)
    headers = await login_admin(client)
    path = f'/api/v1/reviews/projects/{project_id}'
    assert (await client.post(path, json={'action': 'reject', 'comment': '  '}, headers=headers)).status_code == 422
    assert (await client.post(path, json={'action': 'approve'}, headers=headers)).status_code == 200
    assert (await client.patch(path + '/featured', json={'featured': True}, headers=headers)).status_code == 200
    items = (await client.get('/api/v1/reviews/projects?status=published')).json()
    assert any(p['id'] == project_id and p['is_featured'] for p in items)
    assert (await client.post(path, json={'action': 'unpublish'}, headers=headers)).status_code == 200
    assert not any(p['id'] == project_id for p in (await client.get('/api/v1/projects')).json())
    assert (await client.patch(path + '/featured', json={'featured': True}, headers=headers)).status_code == 409

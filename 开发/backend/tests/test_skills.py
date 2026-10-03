import hashlib
import io
import zipfile

import pytest


async def login_user(client, email='skill-author@example.com'):
    payload = {'email': email, 'display_name': 'Skill 作者', 'password': 'StrongPassword123!'}
    await client.post('/api/v1/auth/register', json=payload)
    await client.post('/api/v1/auth/login', json=payload)
    return {'X-CSRF-Token': client.cookies['csrf_token']}


async def approve(client, skill_id):
    await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
    headers = {'X-CSRF-Token': client.cookies['csrf_token']}
    response = await client.patch(f'/api/v1/admin/skills/{skill_id}/status', json={'status': 'published'}, headers=headers)
    assert response.status_code == 200
    return headers


def skill_payload(**changes):
    return dict(name='my-new-skill', summary='发布列表里的简要说明', description='用于代码审查的技能',
                instructions='# 步骤\n\n检查代码和测试。', version='1.0.0', publish=False, **changes)


@pytest.mark.asyncio
async def test_create_manage_and_anonymous_install(client):
    headers = await login_user(client)
    created = await client.post('/api/v1/skills', json=skill_payload(), headers=headers)
    assert created.status_code == 201, created.text
    item = created.json()
    base = '/skills/my-new-skill/1.0.0'
    assert (await client.get(base + '/SKILL.md')).status_code == 404
    assert (await client.get('/api/v1/skills/mine')).json()[0]['id'] == item['id']
    assert (await client.patch(f"/api/v1/skills/{item['id']}/intro", json={'summary': '新的说明'}, headers=headers)).status_code == 200
    published = await client.patch(f"/api/v1/skills/{item['id']}/status", json={'status': 'published'}, headers=headers)
    assert published.json()['summary'] == '新的说明'
    assert published.json()['status'] == 'pending_review'
    assert (await client.get(base + '/download.zip')).status_code == 404
    await approve(client, item['id'])
    client.cookies.clear()
    response = await client.get(base + '/download.zip', headers={'Origin': 'https://external.example'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == '*'
    assert hashlib.sha256(response.content).hexdigest() == item['sha256']
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert '用于代码审查的技能' in archive.read('SKILL.md').decode()
    assert (await client.get(base + '/SKILL.md')).status_code == 200
    assert (await client.get('/api/v1/skills/mine')).status_code == 401
    headers = await login_user(client)
    await client.patch(f"/api/v1/skills/{item['id']}/status", json={'status': 'draft'}, headers=headers)
    assert (await client.get(base + '/download.zip')).status_code == 404
    assert (await client.delete(f"/api/v1/skills/{item['id']}", headers=headers)).status_code == 200
    assert (await client.get('/api/v1/skills/mine')).json() == []


@pytest.mark.asyncio
async def test_skill_ownership_duplicates_and_validation(client):
    headers = await login_user(client)
    created = await client.post('/api/v1/skills', json=skill_payload(), headers=headers)
    item = created.json()
    assert (await client.post('/api/v1/skills', json=skill_payload(), headers=headers)).status_code == 409
    assert (await client.post('/api/v1/skills', json=skill_payload())).status_code == 403
    for field in ['summary', 'description', 'instructions']:
        payload = skill_payload()
        payload[field] = '   '
        assert (await client.post('/api/v1/skills', json=payload, headers=headers)).status_code == 422
    headers = await login_user(client, 'another-author@example.com')
    assert (await client.get('/api/v1/skills/mine')).json() == []
    assert (await client.patch(f"/api/v1/skills/{item['id']}/intro", json={'summary': '篡改'}, headers=headers)).status_code == 404
    assert (await client.patch(f"/api/v1/skills/{item['id']}/status", json={'status': 'published'}, headers=headers)).status_code == 404
    assert (await client.delete(f"/api/v1/skills/{item['id']}", headers=headers)).status_code == 404
    payload = skill_payload()
    payload['version'] = '2.0.0'
    assert (await client.post('/api/v1/skills', json=payload, headers=headers)).status_code == 409


@pytest.mark.asyncio
async def test_upload_preserves_standard_resources_and_accepts_markdown(client):
    headers = await login_user(client)
    md = '---\nname: bundled-skill\ndescription: use --- in a description\n---\n# Steps\nSee references/guide.md\n'
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('bundled-skill/SKILL.md', md)
        archive.writestr('bundled-skill/references/guide.md', 'Guide contents')
        archive.writestr('bundled-skill/scripts/run.py', 'print(1)')
        archive.writestr('bundled-skill/assets/example.bin', b'\x00\xff')
    created = await client.post('/api/v1/skills/upload', data={'version': '1.0.0', 'publish': 'true', 'summary': '自定义说明'},
                                files={'archive': ('skill.zip', stream.getvalue())}, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()['summary'] == '自定义说明'
    uploaded_md = await client.post('/api/v1/skills/upload', data={'version': '2.0.0'},
                                   files={'archive': ('SKILL.md', md.encode())}, headers=headers)
    assert uploaded_md.status_code == 201
    assert uploaded_md.json()['summary'] == 'use --- in a description'
    invalid = await client.post('/api/v1/skills/upload', files={'archive': ('SKILL.md', b'\xff')}, headers=headers)
    assert invalid.status_code == 422
    assert created.json()['status'] == 'pending_review'
    assert (await client.get('/skills/bundled-skill/1.0.0/references/guide.md')).status_code == 404
    await approve(client, created.json()['id'])
    client.cookies.clear()
    base = '/skills/bundled-skill/1.0.0/'
    resource = await client.get(base + 'references/guide.md', headers={'Origin': 'https://external.example'})
    assert resource.text == 'Guide contents'
    assert resource.headers['access-control-allow-origin'] == '*'
    assert (await client.get(base + 'assets/example.bin')).content == b'\x00\xff'
    assert (await client.get(base + 'missing.md')).status_code == 404
    assert (await client.get('/skills/bundled-skill/2.0.0/SKILL.md')).status_code == 404


@pytest.mark.asyncio
async def test_admin_can_add_version_without_taking_ownership(client):
    headers = await login_user(client)
    assert (await client.post('/api/v1/skills', json=skill_payload(), headers=headers)).status_code == 201
    await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
    headers = {'X-CSRF-Token': client.cookies['csrf_token']}
    payload = skill_payload()
    payload['version'] = '2.0.0'
    assert (await client.post('/api/v1/skills', json=payload, headers=headers)).status_code == 201
    await login_user(client)
    assert len((await client.get('/api/v1/skills/mine')).json()) == 2


@pytest.mark.asyncio
async def test_review_rejection_resubmission_and_edit_requires_review(client):
    headers = await login_user(client)
    payload = skill_payload()
    payload['publish'] = True
    item = (await client.post('/api/v1/skills', json=payload, headers=headers)).json()
    assert item['status'] == 'pending_review'
    skill_id = item['id']
    base = '/skills/my-new-skill/1.0.0'
    for suffix in ['/SKILL.md', '/download.zip']:
        assert (await client.get(base + suffix)).status_code == 404
    assert not any(s['slug'] == item['slug'] for s in (await client.get('/api/v1/skills')).json())
    assert (await client.get(f'/api/v1/admin/skills/{skill_id}/review')).status_code == 403
    assert (await client.get(f'/api/v1/admin/skills/{skill_id}/download.zip')).status_code == 403
    assert (await client.patch(f'/api/v1/admin/skills/{skill_id}/status', json={'status': 'published'}, headers=headers)).status_code == 403
    admin_headers = await approve(client, skill_id)
    assert (await client.get(f'/api/v1/admin/skills/{skill_id}/review')).json()['skill_md'].startswith('---')
    assert (await client.get(f'/api/v1/admin/skills/{skill_id}/download.zip')).status_code == 200
    headers = await login_user(client)
    edited = await client.patch(f'/api/v1/skills/{skill_id}/intro', json={'summary': '修改后的简介'}, headers=headers)
    assert edited.json()['status'] == 'pending_review'
    assert (await client.get(base + '/SKILL.md')).status_code == 404
    await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
    admin_headers = {'X-CSRF-Token': client.cookies['csrf_token']}
    url = f'/api/v1/admin/skills/{skill_id}/status'
    assert (await client.patch(url, json={'status': 'rejected', 'review_note': '   '}, headers=admin_headers)).status_code == 422
    rejected = await client.patch(url, json={'status': 'rejected', 'review_note': '请补充使用场景'}, headers=admin_headers)
    assert rejected.json()['status'] == 'rejected'
    headers = await login_user(client)
    assert (await client.get('/api/v1/skills/mine')).json()[0]['review_note'] == '请补充使用场景'
    submitted = await client.patch(f'/api/v1/skills/{skill_id}/status', json={'status': 'published'}, headers=headers)
    assert submitted.json()['status'] == 'pending_review'
    assert submitted.json()['review_note'] is None
    withdrawn = await client.patch(f'/api/v1/skills/{skill_id}/status', json={'status': 'draft'}, headers=headers)
    assert withdrawn.json()['status'] == 'draft'


@pytest.mark.asyncio
async def test_admin_direct_publish_and_reviewer_requires_review(client):
    await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
    headers = {'X-CSRF-Token': client.cookies['csrf_token']}
    payload = skill_payload()
    payload['publish'] = True
    assert (await client.post('/api/v1/skills', json=payload, headers=headers)).json()['status'] == 'published'
    await login_user(client)
    user_id = (await client.get('/api/v1/auth/me')).json()['id']
    await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
    headers = {'X-CSRF-Token': client.cookies['csrf_token']}
    response = await client.patch(f'/api/v1/admin/users/{user_id}/role', json={'role': 'reviewer'}, headers=headers)
    assert response.status_code == 200
    headers = await login_user(client)
    payload['name'] = 'reviewer-skill'
    assert (await client.post('/api/v1/skills', json=payload, headers=headers)).json()['status'] == 'pending_review'

import pytest

from tests.test_admin import login_admin


@pytest.mark.asyncio
async def test_terms_follow_publication_edits_and_removal(client):
    headers = await login_admin(client)
    article = dict(
        slug="automatic-term", title="API Key", summary="用于验证调用者身份的接口密钥。",
        body_markdown="正文不应出现在轻量索引中，这里放足够长的内容。", category="基础概念",
        difficulty="beginner", tags=[], status="draft",
    )
    created = await client.post('/api/v1/admin/wiki', json=article, headers=headers)
    assert created.status_code == 201, created.text
    path = f"/api/v1/admin/wiki/{created.json()['id']}"

    async def index():
        response = await client.get('/api/v1/wiki/terms')
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        return {item['slug']: item for item in response.json()}

    assert article['slug'] not in await index()
    article['status'] = 'published'
    assert (await client.put(path, json=article, headers=headers)).status_code == 200
    assert (await index())[article['slug']] == {
        'slug': article['slug'], 'title': article['title'], 'summary': article['summary'],
    }
    article.update(title='接口密钥', summary='更新后的术语解释会自动出现在课程中。')
    assert (await client.put(path, json=article, headers=headers)).status_code == 200
    assert (await index())[article['slug']]['title'] == '接口密钥'
    assert (await index())[article['slug']]['summary'] == article['summary']
    article['status'] = 'draft'
    assert (await client.put(path, json=article, headers=headers)).status_code == 200
    assert article['slug'] not in await index()

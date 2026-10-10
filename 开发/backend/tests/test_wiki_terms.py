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


@pytest.mark.asyncio
async def test_terms_deduplicate_titles_using_first_published_article(client):
    headers = await login_admin(client)
    common = dict(
        title="重复术语测试", summary="用于验证唯一词条索引。",
        body_markdown="这是一个用于回归测试的词条正文，内容长度满足词条保存校验。", category="基础概念",
        difficulty="beginner", tags=[], status="published",
    )
    first = dict(common, slug="duplicate-term-first")
    second = dict(common, slug="duplicate-term-second", summary="不应成为自动关联的第二个定义。")
    assert (await client.post('/api/v1/admin/wiki', json=first, headers=headers)).status_code == 201
    assert (await client.post('/api/v1/admin/wiki', json=second, headers=headers)).status_code == 201

    response = await client.get('/api/v1/wiki/terms')
    assert response.status_code == 200
    matches = [item for item in response.json() if item['title'] == common['title']]
    assert matches == [{'slug': first['slug'], 'title': first['title'], 'summary': first['summary']}]


@pytest.mark.asyncio
async def test_terms_replace_generated_placeholder_with_definition(client):
    headers = await login_admin(client)
    article = {
        'slug': 'summary-placeholder-term',
        'title': '占位摘要测试',
        'summary': 'Vibe Coding Wiki 词条：占位摘要测试。',
        'body_markdown': '# 占位摘要测试\n\n占位摘要测试是用于验证卡片释义回退逻辑的概念。\n\n补充说明。',
        'category': '基础概念',
        'difficulty': 'beginner',
        'tags': [],
        'status': 'published',
    }
    created = await client.post('/api/v1/admin/wiki', json=article, headers=headers)
    assert created.status_code == 201, created.text

    response = await client.get('/api/v1/wiki/terms')
    assert response.status_code == 200
    match = next(item for item in response.json() if item['slug'] == article['slug'])
    assert match['summary'] == '占位摘要测试是用于验证卡片释义回退逻辑的概念。'

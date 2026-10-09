import pytest


@pytest.mark.asyncio
async def test_public_categories_keep_ancestors_and_category_search_includes_descendants(client):
    await client.post('/api/v1/auth/login', json={
        'email': 'admin@example.com', 'password': 'AdminPassword123!',
    })
    headers = {'X-CSRF-Token': client.cookies['csrf_token']}

    async def category(slug, name, parent_id=None):
        response = await client.post('/api/v1/admin/wiki/categories', headers=headers, json={
            'slug': slug, 'name': name, 'parent_id': parent_id, 'order_index': 5,
        })
        assert response.status_code == 201
        return response.json()

    root = await category('directory-root', '目录父分类')
    child = await category('directory-child', '目录子分类', root['id'])
    leaf = await category('directory-leaf', '目录三级分类', child['id'])
    hidden = await category('directory-hidden', '仅草稿分类', root['id'])

    async def article(slug, item, status):
        response = await client.post('/api/v1/admin/wiki', headers=headers, json={
            'slug': slug, 'title': slug, 'summary': '分类层级测试摘要包含足够多字符',
            'body_markdown': '分类层级测试正文，点击父分类时应包含子分类的公开词条。',
            'category_id': item['id'], 'category': item['name'], 'tags': [], 'status': status,
        })
        assert response.status_code == 201

    await article('directory-published', leaf, 'published')
    await article('directory-draft', hidden, 'draft')
    visible = {item['id']: item for item in (await client.get('/api/v1/wiki/categories')).json()}
    assert all(item['id'] in visible for item in (root, child, leaf))
    assert visible[leaf['id']]['parent_id'] == child['id']
    assert hidden['id'] not in visible
    for item in (root, child, leaf):
        results = (await client.get('/api/v1/wiki', params={'category': item['slug']})).json()
        assert [article['slug'] for article in results['items']] == ['directory-published']
    assert (await client.get('/api/v1/wiki', params={'category': 'missing-category'})).json()['total'] == 0

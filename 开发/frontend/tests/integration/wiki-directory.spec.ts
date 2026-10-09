import { expect, test } from '@playwright/test';

test('wiki sidebar shows nested categories, filters descendants and opens article ancestors', async ({ page, context }) => {
  await context.request.post('/api/v1/auth/login', { data: { email: 'admin@example.com', password: 'AdminPassword123!' } });
  const csrf = (await context.cookies()).find(cookie => cookie.name === 'csrf_token')!.value;
  const headers = { 'X-CSRF-Token': csrf };
  async function createCategory(slug: string, name: string, parent_id: number | null = null) {
    const response = await context.request.post('/api/v1/admin/wiki/categories', { headers, data: { slug, name, parent_id, order_index: 9 } });
    expect(response.status()).toBe(201);
    return response.json();
  }
  const root = await createCategory('browser-wiki-root', '浏览器父分类');
  const child = await createCategory('browser-wiki-child', '浏览器子分类', root.id);
  const leaf = await createCategory('browser-wiki-leaf', '浏览器三级分类', child.id);
  const hidden = await createCategory('browser-wiki-hidden', '浏览器草稿分类', root.id);
  for (const [slug, title, category, status] of [
    ['browser-wiki-parent-article', '父分类词条', child, 'published'],
    ['browser-wiki-leaf-article', '三级分类词条', leaf, 'published'],
    ['browser-wiki-draft-article', '隐藏草稿词条', hidden, 'draft'],
  ] as const) {
    const response = await context.request.post('/api/v1/admin/wiki', { headers, data: {
      slug, title, category_id: category.id, category: category.name, status, tags: [],
      summary: '浏览器目录测试摘要包含足够多字符', body_markdown: '浏览器目录测试正文，验证分类树与词条点击效果。',
    } });
    expect(response.status()).toBe(201);
  }
  await page.goto('/wiki');
  const directory = page.getByRole('navigation', { name: '知识库目录' });
  const parentLink = directory.getByRole('link', { name: root.name, exact: true });
  const childLink = directory.getByRole('link', { name: child.name, exact: true });
  const leafLink = directory.getByRole('link', { name: leaf.name, exact: true });
  const articleLink = directory.getByRole('link', { name: '三级分类词条', exact: true });
  await expect(articleLink).toBeVisible();
  const rootNode = directory.locator('.wiki-tree > .el-tree-node').filter({ has: page.getByRole('link', { name: root.name, exact: true }) });
  const childNode = rootNode.locator(':scope > .el-tree-node__children > .el-tree-node').filter({ has: page.getByRole('link', { name: child.name, exact: true }) });
  const leafNode = childNode.locator(':scope > .el-tree-node__children > .el-tree-node').filter({ has: page.getByRole('link', { name: leaf.name, exact: true }) });
  await expect(leafNode.getByRole('link', { name: '三级分类词条', exact: true })).toBeVisible();
  await expect(directory.getByRole('link', { name: hidden.name, exact: true })).toHaveCount(0);
  await rootNode.locator(':scope > .el-tree-node__content > .el-tree-node__expand-icon').click();
  await expect(childLink).toBeHidden();
  await rootNode.locator(':scope > .el-tree-node__content > .el-tree-node__expand-icon').click();
  await expect(articleLink).toBeVisible();
  await parentLink.click();
  await expect(page).toHaveURL('/wiki?category=browser-wiki-root');
  await expect(page.locator('.result-item')).toHaveCount(2);
  await expect(page.getByLabel('分类', { exact: true })).toHaveValue(root.slug);
  await page.reload();
  await expect(page.locator('.result-item')).toHaveCount(2);
  await childLink.click();
  await expect(page).toHaveURL('/wiki?category=browser-wiki-child');
  await expect(page.locator('.result-item')).toHaveCount(2);
  await leafLink.click();
  await expect(page.locator('.result-item')).toHaveCount(1);
  await articleLink.click();
  await expect(page.locator('.markdown-body')).toContainText('浏览器目录测试正文');
  await expect(articleLink).toHaveAttribute('aria-current', 'page');
  await page.evaluate(() => localStorage.setItem('vcw-directory-mode', 'collapsed'));
  await page.reload();
  await expect(articleLink).toBeVisible();
  await page.screenshot({ path: '.local/wiki-directory-desktop.png', fullPage: true, animations: 'disabled' });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: '打开学习目录' }).click();
  await expect(articleLink).toBeInViewport();
  await page.screenshot({ path: '.local/wiki-directory-mobile.png', fullPage: true, animations: 'disabled' });
  await directory.getByRole('link', { name: '搜索全部词条', exact: true }).click();
  await expect(page).toHaveURL('/wiki');
  await expect(page.getByLabel('分类', { exact: true })).toHaveValue('');
  expect((await context.request.delete(`/api/v1/admin/wiki/categories/${root.id}`, { headers })).ok()).toBeTruthy();
});

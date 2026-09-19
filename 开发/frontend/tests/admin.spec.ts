import { expect, test } from '@playwright/test';

test('admin edits existing wiki and changes account status', async ({ page }) => {
  const admin = { id: 1, email: 'admin@example.com', display_name: '管理员', role: 'admin', is_active: true };
  let active = true;
  let title = '已有词条';
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    let json: unknown = [];
    if (path.endsWith('/auth/me')) json = admin;
    else if (path.endsWith('/admin/users')) json = [admin, { ...admin, id: 2, role: 'user', display_name: '测试用户', is_active: active }];
    else if (path.endsWith('/admin/wiki/categories')) json = [{ id: 7, slug: 'tools', name: '工程工具', parent_id: null, order_index: 0, children: [], article_count: 1 }];
    else if (path.endsWith('/users/2/status')) { active = route.request().postDataJSON().is_active; json = {}; }
    else if (path.endsWith('/admin/wiki/3') && method === 'PUT') { title = route.request().postDataJSON().title; json = {}; }
    else if (path.endsWith('/admin/wiki')) json = [{ id: 3, slug: 'existing', title, summary: '已有摘要足够十个字符用于编辑', body_markdown: '已有正文足够二十个字符用于后台编辑内容验证。', difficulty: 'beginner', category: { id: 7, name: '工程工具', slug: 'tools' }, tags: [], status: 'draft' }];
    await route.fulfill({ json });
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Wiki 编辑', exact: true }).click();
  await page.getByRole('button', { name: '编辑内容', exact: true }).click();
  await expect(page.getByLabel('标题', { exact: true })).toHaveValue('已有词条');
  await page.getByLabel('标题', { exact: true }).fill('修改后的词条');
  await page.getByRole('button', { name: '保存词条' }).click();
  await page.getByRole('button', { name: '用户', exact: true }).click();
  const row = page.getByRole('row').filter({ hasText: '测试用户' });
  await row.getByRole('button', { name: '停用', exact: true }).click();
  await expect(row.getByRole('button', { name: '启用', exact: true })).toBeVisible();
});

test('admin can open the password dialog and submit a password change', async ({ page }) => {
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 1, role: 'admin', display_name: '管理员' } });
    if (path.endsWith('/auth/password')) return route.fulfill({ json: { message: '密码已修改' } });
    return route.fulfill({ json: [] });
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: '修改密码' }).click();
  await page.getByLabel('当前密码').fill('AdminPassword123!');
  await page.getByLabel('新密码', { exact: true }).fill('ChangedPassword456!');
  await page.getByLabel('确认新密码', { exact: true }).fill('ChangedPassword456!');
  await page.getByRole('button', { name: '保存密码' }).click();
  await expect(page.getByText('密码已修改')).toBeVisible();
});

test('reviewer only sees review tools and handles rejected requests', async ({ page }) => {
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 2, role: 'reviewer', display_name: '审核员' } });
    if (route.request().method() === 'POST') return route.fulfill({ status: 403, json: { detail: '不能审核自己的投稿' } });
    return route.fulfill({ json: [{ id: 1, name: '测试项目', summary: '项目摘要', status: 'pending_review', repository_url: 'https://example.com', tech_stack: [], description_markdown: '项目说明' }] });
  });
  await page.goto('/admin');
  await expect(page.getByRole('button', { name: 'Wiki 编辑' })).toHaveCount(0);
  await page.getByRole('button', { name: '通过', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: '不能审核自己的投稿' })).toBeVisible();
});

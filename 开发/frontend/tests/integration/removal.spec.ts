import { test, expect } from '@playwright/test';

test('admin removes categories, entries and other resources with cancel and confirmation', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/vendor/vditor/dist/js/lute/lute.min.js', async route => { await new Promise(resolve => setTimeout(resolve, 1500)); await route.continue(); });
  await page.goto('/login?returnTo=/admin?section=courses');
  await page.getByLabel('邮箱', { exact: true }).fill('admin@example.com');
  await page.getByLabel('密码', { exact: true }).fill('AdminPassword123!');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByRole('button', { name: '新增分类', exact: true })).toBeVisible();
  const cookies = await page.context().cookies();
  const headers = { 'X-CSRF-Token': cookies.find(item => item.name === 'csrf_token')!.value };
  const created = await page.request.post('/api/v1/admin/courses', { headers, data: {
    title: '待移除分类', slug: 'removal-course', difficulty: 'beginner', status: 'published',
    lessons: [{ title: '待移除条目', slug: 'removal-lesson', body_markdown: 'test', status: 'published' }],
  }});
  expect(created.ok()).toBeTruthy();
  await page.reload();
  let row = page.getByRole('row').filter({ hasText: '待移除条目' });
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('待移除条目');
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(row).toHaveCount(0);
  expect((await (await page.request.get('/api/v1/courses/removal-course')).json()).lessons).toEqual([]);
  row = page.getByRole('row').filter({ hasText: '待移除分类' });
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(row).toHaveCount(0);
  expect((await page.request.get('/api/v1/courses/removal-course')).status()).toBe(404);

  // Newly added entries can also be removed before their first save.
  await page.getByRole('button', { name: '新增分类', exact: true }).click();
  await page.getByRole('textbox', { name: '分类名称', exact: true }).fill('本地草稿');
  await page.getByRole('button', { name: '新增条目', exact: true }).click();
  await page.getByRole('button', { name: '移除条目', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(page.getByRole('textbox', { name: '分类名称', exact: true })).toHaveValue('本地草稿');
  await page.getByRole('button', { name: '移除分类', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(page.getByRole('button', { name: '新增分类', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Wiki 编辑', exact: true }).click();
  const wiki = (await (await page.request.get('/api/v1/admin/wiki')).json())[0];
  await page.getByLabel('搜索当前列表').fill(wiki.title);
  row = page.getByRole('row').filter({ hasText: wiki.title });
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(row).toHaveCount(0);
  expect((await page.request.get(`/api/v1/wiki/${wiki.slug}`)).status()).toBe(404);

  await page.getByRole('button', { name: 'Skills', exact: true }).click();
  row = page.locator('.data-table tbody tr').filter({ hasText: 'safe-wiki-research' }).first();
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(row).toHaveCount(0);

  await page.getByRole('button', { name: '审核', exact: true }).click();
  await page.getByLabel('投稿状态').selectOption('published');
  row = page.locator('.data-table tbody tr').filter({ hasText: 'VibeCodingWiki' });
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(row).toHaveCount(0);

  const user = await page.request.post('/api/v1/auth/register', { data: { email: 'remove-ui@example.com', display_name: '可移除用户', password: 'StrongPassword123!' }});
  expect(user.ok()).toBeTruthy();
  await page.getByRole('button', { name: '用户', exact: true }).click();
  await page.getByRole('button', { name: '刷新数据', exact: true }).click();
  row = page.getByRole('row').filter({ hasText: 'remove-ui@example.com' });
  await row.getByRole('button', { name: '移除', exact: true }).click();
  await page.getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(row).toHaveCount(0);
  await expect(page.getByRole('row').filter({ hasText: 'admin@example.com' }).getByRole('button', { name: '移除', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: '审计', exact: true }).click();
  await expect(page.getByRole('cell', { name: 'users.delete', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

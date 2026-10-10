import { expect, test } from '@playwright/test';

test('anonymous visitors open courses directly, switch articles and follow persistent anchors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '课程列表', exact: true })).toBeVisible();
  const catalog = await (await page.request.get('/api/v1/courses')).json();
  expect(catalog.length).toBeGreaterThan(1);
  await expect(page.locator('.course-document-row')).toHaveCount(catalog.length);
  await page.getByLabel('搜索课程').fill('no-matching-course-987654');
  await page.getByRole('button', { name: '搜索当前页面', exact: true }).click();
  await expect(page.getByText('没有匹配的课程，试试其他关键词。')).toBeVisible();
  await page.getByLabel('搜索课程').fill('');
  await page.getByRole('button', { name: '搜索当前页面', exact: true }).click();
  await page.locator('.course-document-row').first().click();
  await expect(page).toHaveURL(`/courses/${catalog[0].slug}`);
  await expect(page.locator('.article-head h1')).toHaveText(catalog[0].lessons[0].title);
  await expect(page.locator('.markdown-body article').first()).toBeAttached();
  await expect(page.getByRole('complementary', { name: '本页目录' })).toBeVisible();
  await page.goto(`/courses/${catalog[1].slug}`);
  await expect(page.locator('.article-head h1')).toHaveText(catalog[1].lessons[0].title);
  await page.setViewportSize({ width: 360, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: '打开学习目录' }).click();
  await page.getByRole('navigation', { name: '课程目录' }).getByRole('link').first().click();
  await expect(page.locator('.article-head h1')).toHaveText(catalog[0].lessons[0].title);
  await expect(page.locator('.docs-sidebar')).not.toHaveClass(/open/);
  expect(errors).toEqual([]);
});

test('sidebar search updates an already open wiki search page', async ({ page }) => {
  await page.goto('/wiki?q=Git');
  await expect(page.getByLabel('搜索知识库', { exact: true })).toHaveValue('Git');
  await page.getByLabel('搜索知识库', { exact: true }).fill('no-matching-wiki-987654');
  await page.getByRole('button', { name: '搜索当前页面', exact: true }).click();
  await expect(page.getByLabel('搜索知识库', { exact: true })).toHaveValue('no-matching-wiki-987654');
  await expect(page.locator('.status-line')).toContainText('找到 0 个词条');
});

test('each course directory entry renders one page and legacy links keep working', async ({ page }) => {
  await page.goto('/');
  const catalog = await (await page.request.get('/api/v1/courses')).json();
  const course = catalog.find((item: { lessons: unknown[] }) => item.lessons.length > 1);
  const directory = page.getByRole('navigation', { name: '课程目录' });
  for (const lesson of course.lessons.slice(0, 2)) {
    await directory.getByRole('link', { name: lesson.title, exact: true }).click();
    await expect(page).toHaveURL(`/courses/${course.slug}/${lesson.slug}`);
    await expect(page.locator('.article-head h1')).toHaveText(lesson.title);
    await expect(page.locator('main .markdown-body')).toHaveCount(1);
    await expect(page.locator('main section[id^="lesson-"]')).toHaveAttribute('id', `lesson-${lesson.slug}`);
    await expect(directory.getByRole('link', { name: lesson.title, exact: true })).toHaveAttribute('aria-current', 'page');
  }
  await page.reload();
  await expect(page.locator('.article-head h1')).toHaveText(course.lessons[1].title);
  await page.goto(`/courses/${course.slug}#lesson-${course.lessons[1].slug}`);
  await expect(page).toHaveURL(`/courses/${course.slug}/${course.lessons[1].slug}`);
  await expect(page.locator('.article-head h1')).toHaveText(course.lessons[1].title);
  await expect(page.locator('main .markdown-body')).toHaveCount(1);
  await page.goto(`/courses/${course.slug}/missing-entry`);
  await expect(page.getByRole('alert')).toContainText('该页面不存在或尚未发布');
  await expect(page.locator('main .markdown-body')).toHaveCount(0);
});

test('wiki article title appears once and section headings stay visible', async ({ page }) => {
  await page.goto('/wiki/git');
  await expect(page.locator('.article-head h1')).toHaveText('Git');
  await expect(page.locator('main').getByRole('heading', { name: 'Git', exact: true })).toHaveCount(1);
  await expect(page.locator('.markdown-body h2')).not.toHaveCount(0);
});

test('compact project cards open content pages, preserve filters and adapt to mobile', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/projects?q=VibeCodingWiki');
  const card = page.locator('.project-card').first();
  await expect(card).toBeVisible();
  const name = await card.locator('h3').innerText();
  await page.locator('.content-toolbar .el-checkbox').click();
  const cardBox = (await card.boundingBox())!;
  const actionsBox = (await card.locator('.project-actions').boundingBox())!;
  expect(cardBox.height).toBeLessThan(210);
  expect(cardBox.x + cardBox.width - actionsBox.x - actionsBox.width).toBeLessThan(20);
  expect(cardBox.y + cardBox.height - actionsBox.y - actionsBox.height).toBeLessThan(20);
  await expect(card.locator('.project-actions .el-icon')).toHaveCount(3);
  await card.getByRole('button', { name: '查看项目说明', exact: true }).click();
  await expect(page).toHaveURL(/\/projects\/[^/?]+\?q=VibeCodingWiki&featured=1$/);
  await expect(page.locator('.project-card')).toHaveCount(0);
  await expect(page.locator('.project-detail h1')).toHaveText(name);
  await expect(page.locator('main').getByRole('heading', { name, exact: true })).toHaveCount(1);
  await expect(page.locator('.project-detail .markdown-body')).not.toBeEmpty();
  await page.screenshot({ path: '.local/project-detail-desktop.png', fullPage: true });
  await page.reload();
  await expect(page.locator('.project-detail h1')).toHaveText(name);
  await page.getByRole('button', { name: '返回作品列表', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: '只看推荐' })).toBeChecked();
  await expect(page.getByLabel('搜索作品', { exact: true })).toHaveValue('VibeCodingWiki');
  await expect(card).toBeInViewport();
  await page.screenshot({ path: '.local/project-cards-desktop.png', fullPage: true });
  await page.getByRole('button', { name: '皮肤 / Theme' }).click();
  await page.getByRole('menuitem', { name: '深色', exact: true }).click();
  await page.screenshot({ path: '.local/project-cards-dark.png', fullPage: true });
  await page.setViewportSize({ width: 360, height: 800 });
  await expect(card).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: '.local/project-cards-mobile.png', fullPage: true });
  await page.getByRole('button', { name: '打开学习目录' }).click();
  await page.getByRole('navigation', { name: '作品目录' }).getByRole('link', { name, exact: true }).click();
  await expect(page.locator('.project-detail h1')).toHaveText(name);
  await expect(page.locator('.docs-sidebar')).not.toHaveClass(/open/);
  expect(errors).toEqual([]);
});

test('header navigation, level filter and reading preferences work and persist', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'GitHub 项目仓库' })).toHaveAttribute('href', 'https://github.com/arknights8037/VibeCodingWiki');
  const catalog = await (await page.request.get('/api/v1/courses')).json();
  await page.getByRole('combobox', { name: '学习等级', exact: true }).press('Enter');
  await page.getByRole('option', { name: '进阶', exact: true }).click();
  const expected = catalog.filter((course: {difficulty: string}) => course.difficulty === 'intermediate').length;
  await expect(page.locator('.course-document-row')).toHaveCount(expected);
  const expectedLessons = catalog
    .filter((course: {difficulty: string}) => course.difficulty === 'intermediate')
    .reduce((count: number, course: {lessons?: unknown[]}) => count + (course.lessons?.length || 1), 0);
  await expect(page.locator('.docs-course-link')).toHaveCount(expectedLessons);
  await page.reload();
  await expect(page.locator('.level-select')).toContainText('进阶');
  await page.getByRole('button', { name: '皮肤 / Theme' }).click();
  await page.getByRole('menuitem', { name: '深色', exact: true }).click();
  await expect(page.locator('.docs-shell')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: '语言 / Language' }).click();
  await expect(page.locator('.wiki-control-popper.wiki-dark-surface:visible')).toHaveCSS('background-color', 'rgb(43, 46, 39)');
  await page.getByRole('menuitem', { name: 'English UI' }).click();
  await expect(page.getByRole('heading', { name: 'Course library', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.locator('.docs-shell')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: /Settings/ }).click();
  await page.getByRole('combobox', { name: '正文字号', exact: true }).press('Enter');
  await page.getByRole('option', { name: 'Large', exact: true }).click();
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  await expect(page.locator('.docs-shell')).toHaveAttribute('data-font', 'large');
  await page.getByRole('button', { name: /Settings/ }).click();
  await page.getByRole('button', { name: 'Reset defaults', exact: true }).click();
  await page.getByRole('button', { name: '完成', exact: true }).click();
  await expect(page.locator('.level-select')).toContainText('全部等级');
  await expect(page.locator('.docs-shell')).toHaveAttribute('data-theme', 'light');
  await page.setViewportSize({ width: 360, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('navigation', { name: '页面切换' }).getByRole('link', { name: '知识库', exact: true }).click();
  await expect(page).toHaveURL('/wiki');
});

test('course groups support persistent fold modes and workspace stays above settings', async ({ page }) => {
  await page.goto('/');
  const group = page.locator('.course-tree > .el-tree-node').first();
  await expect(group.locator(':scope > .el-tree-node__children')).toBeVisible();
  await group.locator(':scope > .el-tree-node__content').click();
  await expect(group.locator(':scope > .el-tree-node__children')).toBeHidden();
  await group.locator(':scope > .el-tree-node__content').click();
  await group.getByRole('link').first().click();
  await expect(page).toHaveURL(/\/courses\/[^/]+\/[^/#]+$/);
  await page.goto('/');
  await page.getByRole('button', { name: /设置/ }).click();
  await page.getByRole('combobox', { name: '目录折叠方式' }).press('Enter');
  await page.getByRole('option', { name: '默认折叠', exact: true }).click();
  await page.getByRole('button', { name: '完成', exact: true }).click();
  await expect(group.locator(':scope > .el-tree-node__children')).toBeHidden();
  await page.reload();
  await expect(group.locator(':scope > .el-tree-node__children')).toBeHidden();
  await page.getByRole('button', { name: /设置/ }).click();
  await page.getByRole('combobox', { name: '目录折叠方式' }).press('Enter');
  await page.getByRole('option', { name: '始终展开，不折叠', exact: true }).click();
  await page.getByRole('button', { name: '完成', exact: true }).click();
  await group.locator(':scope > .el-tree-node__content').click();
  await expect(group).toHaveAttribute('aria-expanded', 'true');
  await expect(group.locator(':scope > .el-tree-node__children')).toBeVisible();
  await page.goto('/login');
  await page.getByLabel('邮箱', { exact: true }).fill('admin@example.com');
  await page.getByLabel('密码', { exact: true }).fill('AdminPassword123!');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.locator('.sidebar-workspace')).toBeVisible();
  const workspace = await page.locator('.sidebar-workspace').boundingBox();
  const settings = await page.locator('.sidebar-settings').boundingBox();
  expect(workspace!.y + workspace!.height).toBeLessThanOrEqual(settings!.y + 1);
  await expect(page.locator('.sidebar-directory .sidebar-workspace')).toHaveCount(0);
  await expect(page.locator('.level-select .el-select__wrapper')).toHaveCSS('min-height', '36px');
});

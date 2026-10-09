import { expect, test, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

async function login(page: Page, email = "admin@example.com", password = "AdminPassword123!") {
  await page.goto("/auth");
  await page.getByLabel("邮箱", { exact: true }).fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("button", { name: "退出", exact: true })).toBeVisible();
}

async function fillProject(page: Page, name: string, slug: string) {
  await page.getByLabel("项目名称", { exact: true }).fill(name);
  await page.getByLabel("英文标识", { exact: true }).fill(slug);
  await page.getByLabel("一句话摘要").fill("这是一个用于验证完整投稿流程的开源演示项目。");
  await page.getByLabel("详细说明 Markdown").fill("# 测试作品\n\n这个作品用于验证保存、修改、审核和公开展示的完整流程。");
  await page.getByLabel("公开仓库地址").fill("https://example.com/repository");
  await page.getByLabel("演示地址 可选").fill("https://example.com/demo");
  await page.getByLabel("技术栈 逗号分隔").fill("HTML, JavaScript");
  const category = page.getByLabel("内容分区");
  if (await category.count()) await category.selectOption({ index: 1 });
}

test("anonymous admin entry returns to the dashboard after login and survives reload", async ({ page }) => {
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/login\?returnTo=\/admin$/);
  await page.getByLabel("邮箱", { exact: true }).fill("admin@example.com");
  await page.getByLabel("密码", { exact: true }).fill("AdminPassword123!");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "后台管理", exact: true })).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "后台管理", exact: true })).toBeVisible();
});

test("anonymous pages, wiki search, deep links and skill download use the real API", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  for (const path of ["/", "/wiki", "/projects", "/skills", "/auth"]) {
    const response = await page.goto(path);
    expect(response?.status()).toBe(200);
    await expect(page.locator(".page, .auth-screen").first()).toBeVisible();
  }
  await page.goto("/skills");
  await page.reload();
  const raw = await page.request.get("/skills/safe-wiki-research/1.0.0/SKILL.md");
  expect(raw.ok()).toBeTruthy();
  expect(await raw.text()).toContain("name: safe-wiki-research");
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "下载 ZIP" }).first().click();
  expect((await download).suggestedFilename()).toBe("safe-wiki-research-1.0.0.zip");
  await page.goto("/wiki");
  await page.getByLabel("搜索知识库", { exact: true }).fill("Git");
  await page.getByRole("button", { name: "查询", exact: true }).click();
  await page.getByRole("heading", { name: "Git", exact: true }).click();
  await expect(page.locator(".markdown-body")).toContainText("Git");
  await page.reload();
  await expect(page.locator(".markdown-body")).toContainText("Git");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/wiki");
  await page.screenshot({ path: info.outputPath("wiki-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 360, height: 800 });
  for (const path of ["/", "/wiki", "/skills", "/projects", "/auth"]) {
    await page.goto(path);
    await expect(page.locator(".page, .auth-screen").first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  }
  await page.goto("/skills");
  await expect(page.getByRole("link", { name: "下载 ZIP" }).first()).toBeVisible();
  await page.screenshot({ path: info.outputPath("skills-mobile.png"), fullPage: true });
  expect(errors).toEqual([]);
});

test("registration, draft editing, rejection, resubmission, publishing and unpublishing", async ({ page, browser }) => {
  const suffix = Date.now();
  const name = `完整 UI 项目 ${suffix}`;
  await page.goto("/projects/submit");
  await expect(page).toHaveURL(/login\?returnTo=/);
  await page.getByRole("link", { name: "立即注册", exact: true }).click();
  await page.getByLabel("显示名称").fill("端到端投稿者");
  await page.getByLabel("邮箱", { exact: true }).fill(`author-${suffix}@example.com`);
  await page.getByLabel("密码", { exact: true }).fill("StrongPassword123!");
  await page.getByLabel("确认密码", { exact: true }).fill("StrongPassword123!");
  await page.getByRole("button", { name: "注册并登录" }).click();
  await expect(page).toHaveURL(/\/projects\/submit$/);
  await fillProject(page, name, `ui-project-${suffix}`);
  await page.getByRole("button", { name: "保存草稿", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: name })).toContainText("draft");
  await page.getByRole("link", { name: "编辑重投" }).click();
  await expect(page.getByLabel("项目名称", { exact: true })).toHaveValue(name);
  await page.getByRole("button", { name: "保存并提交审核" }).click();
  await expect(page.getByRole("row").filter({ hasText: name })).toContainText("pending_review");

  const adminContext = await browser.newContext();
  const admin = await adminContext.newPage();
  await login(admin);
  await admin.goto("/admin");
  const row = admin.getByRole("row").filter({ hasText: name });
  await row.getByRole("button", { name: "驳回", exact: true }).click();
  await admin.getByRole("dialog").locator("textarea").fill("请补充运行方法");
  await admin.getByRole("dialog").getByRole("button", { name: /^(OK|确定)$/ }).click();
  await expect(row).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("row").filter({ hasText: name })).toContainText("请补充运行方法");
  await page.getByRole("link", { name: "编辑重投" }).click();
  await page.getByLabel("详细说明 Markdown").fill("# 已补充运行方法\n\n下载仓库后打开 index.html，即可看到这个项目的完整界面。");
  await page.getByRole("button", { name: "保存并提交审核" }).click();
  await expect(page).toHaveURL(/\/projects\/mine$/);
  await admin.reload();
  await row.getByRole("button", { name: "通过", exact: true }).click();
  await expect(row).toHaveCount(0);
  await admin.getByLabel("投稿状态").selectOption("published");
  await row.getByRole("button", { name: "设为推荐" }).click();
  await expect(row.getByRole("button", { name: "取消推荐" })).toBeVisible();
  await page.goto("/projects");
  const card = page.locator(".project-card").filter({ hasText: name });
  await expect(card.getByRole("link", { name: "打开演示" })).toHaveAttribute("href", "https://example.com/demo");
  await card.getByRole("button", { name: "查看项目说明", exact: true }).press("Enter");
  await expect(page.locator(".project-card")).toHaveCount(0);
  await expect(page.locator(".project-detail .markdown-body")).toContainText("已补充运行方法");
  await page.getByRole("button", { name: "返回作品列表", exact: true }).click();
  await expect(card).toBeVisible();
  await expect(card.locator(".markdown-body")).toHaveCount(0);
  await row.getByRole("button", { name: "取消发布" }).click();
  await admin.getByRole("dialog").getByRole("button", { name: /^(OK|确定)$/ }).click();
  await expect(row).toHaveCount(0);
  await page.reload();
  await expect(card).toHaveCount(0);
  await admin.getByRole("button", { name: "审计", exact: true }).click();
  await expect(admin.getByText("project.reject", { exact: true }).first()).toBeVisible();
  await admin.getByRole("button", { name: "退出", exact: true }).click();
  await expect(admin).toHaveURL("/");
  await admin.goto("/admin");
  await expect(admin).toHaveURL(/\/login\?returnTo=\/admin$/);
  await adminContext.close();
});

test("admin wiki lifecycle and user role / account controls", async ({ page, browser }) => {
  const suffix = Date.now();
  const title = `浏览器编辑词条${suffix}`;
  await login(page);
  await page.goto("/admin");
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === "csrf_token")!.value;
  const categoryList = await (await page.request.get("/api/v1/admin/wiki/categories")).json();
  const categoryId = categoryList[0].id;
  const createdWiki = await page.request.post("/api/v1/admin/wiki", {
    headers: { "X-CSRF-Token": csrf },
    data: { slug: `browser-wiki-${suffix}`, title, summary: "浏览器测试创建的完整词条摘要，验证搜索和发布。", body_markdown: "# 浏览器测试\n\n这是通过真实浏览器保存的词条正文，能够被访客检索和阅读。", category_id: categoryId, category: categoryList[0].name, tags: [], difficulty: "beginner", status: "published" },
  });
  expect(createdWiki.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Wiki 编辑", exact: true }).click();
  await expect(page.getByText(title, { exact: true })).toBeVisible();
  let row = page.locator('tr').filter({ hasText: title });
  const visitor = await browser.newContext();
  const reader = await visitor.newPage();
  await reader.goto(`/wiki?q=${title}`);
  await expect(reader.getByRole("heading", { name: title })).toBeVisible();
  await row.getByRole("button", { name: "编辑内容", exact: true }).click();
  await page.getByRole("combobox", { name: "词条状态", exact: true }).click({ force: true });
  await page.getByRole("option", { name: "草稿", exact: true }).click();
  await page.getByRole("button", { name: "保存词条" }).click();
  await page.getByRole("button", { name: "返回列表", exact: true }).click();
  row = page.locator('tr').filter({ hasText: title });
  await expect(row).toContainText("草稿");
  await reader.reload();
  await expect(reader.locator(".status-line")).toContainText("找到 0 个词条");
  await reader.goto("/auth");
  await reader.getByRole("link", { name: "立即注册", exact: true }).click();
  await reader.getByLabel("显示名称").fill(`账号测试${suffix}`);
  await reader.getByLabel("邮箱", { exact: true }).fill(`role-${suffix}@example.com`);
  await reader.getByLabel("密码", { exact: true }).fill("StrongPassword123!");
  await reader.getByLabel("确认密码", { exact: true }).fill("StrongPassword123!");
  await reader.getByRole("button", { name: "注册并登录" }).click();
  await expect(reader.getByRole("button", { name: "退出" })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "用户", exact: true }).click();
  const userRow = page.getByRole("row").filter({ hasText: `role-${suffix}@example.com` });
  const roleSelect = userRow.getByRole("combobox", { name: /的角色$/ });
  await roleSelect.click({ force: true });
  await page.getByRole("option", { name: "审核员", exact: true }).click();
  await expect.poll(async () => {
    const users = await (await page.request.get("/api/v1/admin/users")).json();
    return users.find((item: { email: string }) => item.email === `role-${suffix}@example.com`)?.role;
  }).toBe("reviewer");
  await reader.goto("/admin");
  await expect(reader.getByRole("heading", { name: "后台管理" })).toBeVisible();
  await expect(reader.getByRole("button", { name: "Wiki 编辑" })).toHaveCount(0);
  await userRow.getByRole("button", { name: "停用", exact: true }).click();
  await expect(userRow.getByRole("button", { name: "启用", exact: true })).toBeVisible();
  await reader.reload();
  await expect(reader).toHaveURL(/\/login\?returnTo=\/admin$/);
  await userRow.getByRole("button", { name: "启用", exact: true }).click();
  await expect(userRow.getByRole("button", { name: "停用", exact: true })).toBeVisible();
  await visitor.close();
});

test("admin uploads, downloads and unpublishes a real Skill archive", async ({ page }) => {
  const slug = `ui-skill-${Date.now()}`;
  const archive = execFileSync("../backend/.venv/Scripts/python.exe", ["-c",
    "import io,sys,zipfile; b=io.BytesIO(); z=zipfile.ZipFile(b,'w'); z.writestr('SKILL.md','---\\nname: '+sys.argv[1]+'\\ndescription: A browser tested skill package\\n---\\n# Steps\\nRead the wiki.'); z.close(); sys.stdout.buffer.write(b.getvalue())", slug]);
  await login(page);
  await page.goto("/admin");
  await page.getByRole("button", { name: "Skills", exact: true }).click();
  await page.getByLabel("选择 Skill 文件").setInputFiles({ name: "skill.zip", mimeType: "application/zip", buffer: archive });
  await page.getByRole("combobox", { name: "内容分区", exact: true }).click({ force: true });
  await page.getByRole("option").first().click();
  await page.locator('.el-checkbox').click();
  await page.getByRole("button", { name: "保存并发布", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: slug });
  await expect(row).toContainText("已发布");
  const catalog = await (await page.request.get("/api/v1/skills")).json();
  const skill = catalog.find((item: { slug: string }) => item.slug === slug);
  const downloaded = await page.request.get(`/skills/${slug}/1.0.0/download.zip`);
  expect(downloaded.ok()).toBeTruthy();
  expect(createHash("sha256").update(await downloaded.body()).digest("hex")).toBe(skill.sha256);
  await row.getByRole("button", { name: "下架", exact: true }).click();
  await expect(row).toContainText("草稿");
  expect((await page.request.get(`/skills/${slug}/1.0.0/download.zip`)).status()).toBe(404);
});

test("expired access cookie is refreshed without asking the user to log in again", async ({ page, context }) => {
  await login(page);
  const access = (await context.cookies()).find(cookie => cookie.name === "access_token")!;
  await context.addCookies([{ ...access, value: "expired-access-token" }]);
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "后台管理" })).toBeVisible();
  expect((await context.cookies()).find(cookie => cookie.name === "access_token")?.value).not.toBe("expired-access-token");
});

test("account center keeps the global header and adapts to mobile", async ({ page }) => {
  await login(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "账户中心", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "页面切换" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "账户设置" })).toBeVisible();
  await expect(page.getByRole("button", { name: /个人信息/ })).toHaveAttribute("aria-current", "page");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("navigation", { name: "页面切换" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.getByRole("button", { name: /账号安全/ }).click();
  await expect(page).toHaveURL(/\/profile\/security$/);
  await expect(page.getByRole("heading", { name: "账号安全", exact: true })).toBeVisible();
});


test("independent admin workspace keeps its section, searches documents and supports mobile navigation", async ({ page }) => {
  await login(page);
  await page.goto('/admin?section=wiki');
  await expect(page.locator('.workspace-sidebar')).toBeVisible();
  await expect(page.locator('.topbar')).toHaveCount(0);
  await expect(page.locator('.workspace-topbar').getByText('知识库内容', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('知识库目录', { exact: false }).first()).toBeVisible();
  await page.getByRole('button', { name: '编辑内容', exact: true }).first().click();
  await expect(page.getByRole('region', { name: '正文编辑区' })).toBeVisible();
  await page.locator('.editor-shell__content[contenteditable="true"]').fill('未保存的知识库修改');
  await page.getByRole('button', { name: '用户', exact: true }).click({ force: true });
  await expect(page.getByRole('dialog')).toContainText('当前修改尚未保存');
  await page.getByRole('dialog').getByRole('button', { name: '继续编辑', exact: true }).click();
  await expect(page).toHaveURL(/section=wiki/);
  await page.goto('/admin?section=wiki');
  await expect(page.locator('.workspace-sidebar')).toBeVisible();
  await page.setViewportSize({ width: 360, height: 800 });
  await expect(page.locator('.workspace-sidebar')).toBeVisible();
  await page.goto('/admin?section=users');
  await expect(page).toHaveURL(/section=users/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

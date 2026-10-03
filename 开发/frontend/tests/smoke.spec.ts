import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ status: 401, json: { detail: "请先登录" } }),
  );
  await page.route("**/api/v1/courses", (route) =>
    route.fulfill({
      json: [
        {
          id: 1,
          slug: "vibe-coding-basics",
          title: "Vibe Coding 基本概念与风险",
          summary: "理解工作方式与边界",
          prerequisites: "无",
          difficulty: "beginner",
          order_index: 1,
          lessons: [],
        },
      ],
    }),
  );
  await page.route("**/api/v1/wiki**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            id: 1,
            slug: "git",
            title: "Git",
            summary: "分布式版本控制系统",
            difficulty: "beginner",
            category: { slug: "tools", name: "工程工具" },
            tags: [],
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
        page: 1,
        page_size: 4,
      },
    }),
  );
});

test("homepage exposes the learning path and search", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "课程列表", exact: true })).toBeVisible();
  await expect(
    page.locator("main").getByRole("link", { name: /Vibe Coding 基本概念/ }),
  ).toBeVisible();
  await page.getByRole("navigation", {name:"页面切换"}).getByRole("link", {name:"知识库", exact:true}).click();
  await page.getByLabel("搜索知识库", {exact:true}).fill("Git");
  await page.getByRole("button", {name:"搜索当前页面", exact:true}).click();
  await expect(page).toHaveURL(/\/wiki\?q=Git/);
});

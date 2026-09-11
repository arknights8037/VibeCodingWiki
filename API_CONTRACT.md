# API 契约

## 通用约定

- REST 前缀：`/api/v1`；JSON 使用 UTF-8。
- 成功列表使用 `{items, page, page_size, total}`；`page` 从 1 开始，默认每页 20，最大 100。
- FastAPI 校验错误为 `422`；业务错误统一为 `{"detail":"中文说明"}`。
- `401` 未登录/令牌失效，`403` 权限不足或 CSRF 失败，`404` 不存在，`409` 唯一性或状态冲突。
- 浏览器自动携带 HttpOnly Cookie；`POST/PUT/PATCH/DELETE` 还要发送 `X-CSRF-Token`，其值来自 `csrf_token` Cookie。

## Auth

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | `{email,password,display_name}`，创建 user 并登录 |
| POST | `/auth/login` | `{email,password}`，设置 access/refresh/csrf Cookie |
| POST | `/auth/refresh` | 轮换刷新令牌与访问令牌 |
| POST | `/auth/logout` | 撤销刷新令牌并清 Cookie，需要 CSRF |
| GET | `/auth/me` | 当前用户 |

## Courses / Wiki

- `GET /courses`：按模块顺序返回发布课程与课文目录。
- `GET /courses/{slug}`、`GET /courses/lessons/{slug}`：课程或课文详情。
- `PUT /courses/lessons/{slug}/complete`、`DELETE .../complete`：进度幂等写入。
- `GET /wiki`：参数 `q`、`phrase`、`category`、重复 `tag`、`difficulty`、`updated_after`、`sort=relevance|updated_desc|title_asc`、`page`、`page_size`。
- `GET /wiki/{slug}`、`GET /wiki/meta/categories`、`GET /wiki/meta/tags`。

## Projects / Reviews / Admin

- `GET /projects` 仅发布态；`GET /projects/mine` 返回本人全部投稿。
- `POST /projects` 创建草稿；`PUT /projects/{id}` 只允许本人修改草稿/驳回稿；`POST /projects/{id}/submit` 提交审核。
- `GET /reviews/projects` 返回待审列表；`POST /reviews/projects/{id}` body 为 `{action: approve|reject|unpublish, comment?, featured?}`。
- `/admin/users` 管理激活状态与角色；`/admin/wiki` 管理词条；`/admin/skills/upload` 校验 ZIP；`/admin/audit-logs` 只读分页。

投稿状态转换：

```text
draft ──submit──> pending_review ──approve──> published
  ▲                    │                         │
  │                    └──reject──> rejected ───┘(重新编辑后 submit)
  └──────────────────unpublish───────────────────
```

## Skills

- `GET /api/v1/skills`：发布包目录、版本、兼容性、SHA-256、相对下载地址。
- `GET /skills/{slug}/{version}/SKILL.md`：`text/plain` 原文。
- `GET /skills/{slug}/{version}/download.zip`：确定性 ZIP；其字节 SHA-256 等于目录字段。

## MCP

- Streamable HTTP：`POST/GET/DELETE /mcp`，协议目标 `2026-07-28`。
- 工具输入/输出：
  - `search_wiki(q, category?, limit=10)` → `{slug,title,summary}[]`
  - `get_wiki_article(slug)` → 完整发布词条或 `error`
  - `list_courses()` → 课程摘要数组
  - `get_lesson(slug)` → 完整发布课文或 `error`
  - `list_projects(limit=20)` → 发布项目数组
  - `list_skills()` → 发布 Skill 数组
- 资源：`wiki://articles/{slug}`、`course://lessons/{slug}`。
- MCP 不支持写入、登录、草稿、投稿人、审核或管理员信息。

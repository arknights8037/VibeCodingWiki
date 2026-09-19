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
| POST | `/auth/password` | `{current_password,new_password}`，修改当前账号密码，需要 CSRF |
| PATCH | `/auth/profile` | 修改用户名、真名和头像地址 |
| POST | `/auth/avatar` | multipart 文件上传头像（JPG/PNG/WEBP/GIF，最大 2MB） |
| PATCH | `/auth/social-accounts` | 保存绑定账号信息，需要 CSRF |
| GET | `/auth/notifications` | 当前用户的投稿状态通知 |
| GET | `/auth/oauth/{github|gitee}/start` | 跳转至对应平台官方 OAuth 授权 |
| GET | `/auth/oauth/{github|gitee}/callback` | OAuth 回调并持久化绑定用户名 |
| POST | `/auth/mcp-token` | 轮换当前用户 MCP 凭据，需要 CSRF |

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
- `/admin/users` 管理激活状态与角色；`/admin/wiki` 管理词条；`/admin/skills/upload` 校验 ZIP；`/admin/audit-logs` 返回操作者、动作、目标、时间及结构化 detail 详情。

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

## 后台管理补充接口

以下管理写接口均要求 CSRF Header；`/admin/*` 仅允许 admin。

| 方法 | 路径（前缀 `/api/v1`） | 用途 |
|---|---|---|
| GET | `/admin/wiki` | 获取含正文、状态的词条列表（包括草稿） |
| PUT | `/admin/wiki/{id}` | 更新词条，状态仅允许 draft/published，slug 冲突返回 409 |
| PATCH | `/admin/users/{id}/status` | `{ "is_active": false }` 停用账号并撤销刷新令牌 |
| GET/PATCH | `/admin/oauth/settings` | 管理员查看或配置 GitHub/Gitee OAuth Client ID/Secret；Secret 不回显 |
| GET | `/admin/skills` | 获取含 id、状态的全部 Skill 版本 |
| PATCH | `/admin/skills/{id}/status` | `{ "status": "draft" }` 下架，published 发布 |
| GET | `/reviews/projects?status=published` | 按状态获取投稿，默认 pending_review；reviewer/admin |
| PATCH | `/reviews/projects/{id}/featured` | `{ "featured": true }` 推荐已发布项目；禁止操作自己的投稿 |

Skills 下架后公开目录与下载均不可访问，管理列表仍可查看。管理操作写入审计日志。


### 课程编辑（管理员）
- `GET /api/v1/admin/courses`：包含草稿和发布状态的完整两级目录。
- `POST /api/v1/admin/courses`：新建一级分类及课文。
- `PUT /api/v1/admin/courses/{id}`：保存分类与所有课文，写入操作审计；写操作要求 CSRF。
- 分类包含 `difficulty`、`order_index`、`directory_collapsible`、`status`；课文包含 Markdown 正文、目标、实践、验收、排序及状态。
- 已有课文保留 ID 和学习进度；隐藏内容使用草稿或归档，不支持通过省略课文来删除。标识冲突返回 409，目录 ID 不匹配返回 422。
- 公开课程列表与详情仅包含已发布分类和已发布课文。


### 移除内容（管理员）
`DELETE /api/v1/admin/{resource}/{id}`，resource 支持 `courses`、`lessons`、`wiki`、`projects`、`skills`、`users`。仅管理员可调用，要求 CSRF，成功返回消息，重复移除返回 404。
分类移除级联清理课文与学习进度；条目移除清理自身进度；Wiki 移除同步清理标签关系与全文索引；Skill 仅移除指定版本。用户移除清理其登录令牌、投稿和学习进度，既有审计记录保留并解除 actor 外键。当前账号或具有审核历史的账号不能移除（409），后者可停用。移除动作记录资源名称与 ID，审计日志无移除入口。

### 知识库目录管理（管理员）
- `GET /api/v1/admin/wiki/categories`：返回可无限层级嵌套的分类树，包含词条数与同级顺序。
- `POST/PUT /api/v1/admin/wiki/categories[/{id}]`：新增或编辑分类，正文支持 `slug`、`name`、`parent_id`、`order_index`；父级不能为自身。
- `DELETE /api/v1/admin/wiki/categories/{id}`：仅允许删除没有子分类和词条的空分类。
- `POST /api/v1/admin/wiki/categories/{id}/move`、`POST /api/v1/admin/wiki/{id}/move`：按 `offset: -1|1` 调整同级分类或同分类词条位置，边界返回 409。
- Wiki 写入支持 `category_id` 与 `order_index`，仍兼容按名称自动创建分类。


### 目录排序与无分类条目
- `POST /api/v1/admin/{courses|lessons}/{id}/move`，正文 `{ "offset": -1 }` 或 `{ "offset": 1 }`。同等级根节点或同分类条目交换相邻位置，单次事务保存全部兄弟节点顺序；边界返回 409。要求管理员和 CSRF，并记录审计。
- `Course.is_standalone` 标识无分类根条目；复用课程阅读路由及课文进度记录，必须且只能有一篇正文，标题、标识及发布状态以正文条目为准。前后台目录直接展示为叶子链接。分类与无分类条目共同排序；删除独立正文同时清理其承载记录。

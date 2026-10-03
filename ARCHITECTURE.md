# 架构说明

## 组件关系

```text
Browser / MCP Client
        │
        ▼
Nginx :80 ── static Vue SPA
   ├── /api/* ─────────┐
   ├── /mcp ───────────┤
   └── /skills/* ──────┤
                       ▼
             FastAPI / Uvicorn (1 worker)
              ├── REST + RBAC + CSRF
              ├── MCP session manager
              ├── FTS5 search service
              └── Skill archive validator
                       │
                       ▼
             SQLite + named data volume
                       └── media/avatars（用户头像文件）
```

浏览器与后端同源，避免 CORS、Cookie 与 CSRF 配置分叉。Nginx 只负责静态文件与反向代理，应用约束集中在 FastAPI。

## 后端分层

- `api/`：HTTP 输入输出、鉴权依赖、状态码。
- `services/`：FTS 查询与 Skill 安全校验，可独立测试。
- `models.py`：SQLAlchemy 2 模型与枚举。
- `schemas.py`：Pydantic 2 请求/响应契约。
- `mcp_server.py`：公开只读工具和资源，复用数据库与搜索服务。
- `alembic/`：版本化数据库初始化；FTS5 表和触发器与结构一起迁移。

## 数据流

### Wiki 查询

请求参数经 Pydantic 校验；服务将关键词和精确短语转为受限 FTS5 token，其他条件以 SQLAlchemy 绑定参数组合；只查询 `published`，最后分页并返回总数。前端将 Markdown 转 HTML 后再用 DOMPurify 清理。

### 认证与写操作

登录验证 Argon2 后签发短期 JWT 访问 Cookie和随机刷新 Cookie；刷新令牌数据库只存 SHA-256。刷新时撤销旧令牌并轮换。写操作同时要求登录 Cookie 和 `X-CSRF-Token` 与可读 CSRF Cookie 相等。

### 投稿审核

作者只能推动自己的 `draft/rejected → pending_review`。审核端在事务内验证角色、非本人和当前状态，更新投稿、追加 ReviewEvent，并写 AuditLog。发布列表永远筛选 `published`。

### MCP 生命周期

公开 MCP ASGI 应用挂载在 FastAPI 最后一个路由；管理员写入端点 `/mcp/admin` 在其前面挂载并始终校验 Bearer 凭证。顶层 lifespan 显式进入两个 MCP session manager，避免挂载子应用的 lifespan 不执行。公开 MCP 函数重新进行发布态过滤，管理员写入函数记录独立审计事件。

### 账户中心与 OAuth

账户中心沿用文档站 ShellLayout 的顶部品牌头部，头像入口进入账户路由后隐藏课程目录和其他页面内容，仅呈现账户二级菜单。个人资料和安全操作通过受 CSRF 保护的 REST 接口保存；头像以 multipart 上传至数据目录并通过 `/media` 静态挂载访问。管理员在 `/admin?section=mcp` 配置 GitHub/Gitee OAuth 凭据，用户绑定时经过官方授权页、state Cookie 校验和官方用户接口读取用户名，不在浏览器保存第三方令牌。

## SQLite 设计

启动连接设置 `PRAGMA journal_mode=WAL`、`foreign_keys=ON`、`busy_timeout=5000`。FTS5 外部内容表覆盖 Wiki 标题、摘要、正文以及课程正文，并用触发器保持一致。首版严格单 worker；需要多实例时先迁移到 PostgreSQL，再评估专用全文检索。

## 安全策略

- 最小权限 RBAC；后台前端隐藏不等于授权，后端逐路由校验。
- HttpOnly、SameSite=Lax Cookie，生产 HTTPS 设置 Secure；CSRF 双提交。
- Markdown 仅在浏览器端白名单净化；不允许服务端执行内容。
- ZIP 在解压前后限制大小/数量并验证路径；分发使用确定性重建包。
- 审核和管理员写操作写入 append-only 业务记录；日志避免敏感值。
- 依赖范围锁在主版本内，CI 执行静态检查、测试和镜像构建。

## 技术选型理由

Vue 3/TypeScript 适合内容型 SPA 和类型化组件；FastAPI/Pydantic 提供清晰契约；SQLAlchemy/Alembic 保持未来迁移空间；SQLite 适合课程级单机部署；Nginx 统一入口；官方 MCP SDK 降低协议偏差。Pinia 只保存当前用户状态，不在浏览器持久化令牌。

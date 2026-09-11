# VibeCodingWiki

VibeCodingWiki 是面向零基础学习者的中文 Vibe Coding 知识平台。它把课程路径、可检索 Wiki、开源项目投稿、Agent Skills 分发、MCP 只读服务和内容后台放进一个可在单机 Docker 环境运行的项目。

## 首版能力

- 9 个递进课程模块，每个模块含目标、前置知识、完整示例课文、实践任务和完成标准。
- 20 个预置 Wiki 词条，支持中文全文检索、精确短语、分类、标签、难度、更新时间、分页与相关度排序。
- `user` 投稿，`reviewer` / `admin` 审核、驳回、发布、取消发布和置顶；审核历史不可覆盖。
- 6 个只读 MCP 工具与对应资源，仅暴露已发布内容。
- Agent Skills ZIP 校验、稳定下载地址、原始 `SKILL.md` 与 SHA-256。
- Vue 3 管理后台，覆盖审核、用户角色、Wiki、Skills 与审计日志。

首版明确不含评论、点赞、收藏、举报、通知、OAuth 与邮件找回密码。

## Docker 快速启动

1. 复制环境变量并至少修改密钥和管理员密码：

   ```powershell
   Copy-Item .env.example .env
   ```

2. 构建并启动：

   ```powershell
   docker compose up --build
   ```

3. 打开 `http://localhost:8088`。健康检查在 `http://localhost:8088/healthz`，REST 文档在 `http://localhost:8088/docs`，MCP 入口为 `http://localhost:8088/mcp`。如宿主机 80 端口可用，可在 `.env` 设置 `VCW_HTTP_PORT=80` 恢复无端口号入口。

启动时会运行 Alembic、写入种子内容，并按 `.env` 创建或更新管理员。默认示例值仅供本地演示：`admin@example.com` / `ChangeMe123!`，公开部署前必须替换。

SQLite、Skills 和上传数据位于命名卷 `vibecodingwiki_data`，容器重建不会删除；首版只支持一个后端实例。

## 本地开发

后端要求 Python 3.13：

```powershell
cd 开发/backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
.venv/Scripts/uvicorn app.main:app --reload
```

前端要求 Node 22 与 pnpm：

```powershell
cd 开发/frontend
pnpm install
pnpm dev
```

测试命令：

```powershell
cd 开发/backend; .venv/Scripts/ruff check .; .venv/Scripts/pytest
cd 开发/frontend; pnpm test; pnpm build; pnpm test:e2e
```

## 目录

```text
开发/frontend/   Vue 3 + TypeScript + Vite
开发/backend/    FastAPI + SQLAlchemy + Alembic + SQLite
文档/            填写版需求报告、周报、开题 PPT 与绘图清单
.github/         CI、Issue 与 PR 模板
```

规划、需求、架构和接口分别见 [PROJECT_PLAN.md](PROJECT_PLAN.md)、[REQUIREMENTS.md](REQUIREMENTS.md)、[ARCHITECTURE.md](ARCHITECTURE.md) 和 [API_CONTRACT.md](API_CONTRACT.md)。贡献与安全要求见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

## MCP 与 Skills

MCP 目标规范为 `2026-07-28`。工具：`search_wiki`、`get_wiki_article`、`list_courses`、`get_lesson`、`list_projects`、`list_skills`。服务不会返回草稿、投稿人资料或后台数据。

Skills 的稳定地址形式：

```text
/skills/{slug}/{version}/SKILL.md
/skills/{slug}/{version}/download.zip
```

平台只检查并分发 Skill，不执行上传包内脚本。

## Git 工作流

仓库使用 `main`、`develop`、`feat/*`、`fix/*`，提交遵循 Conventional Commits。`main` 应在 GitHub 中设置为仅允许 PR 合并；远程仓库与首次 push 需由仓库所有者授权。

## 许可证

[MIT](LICENSE)

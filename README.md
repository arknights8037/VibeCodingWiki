# VibeCodingWiki

VibeCodingWiki 是面向零基础学习者的中文 Vibe Coding 知识平台。它提供课程路径、可检索 Wiki、开源项目投稿、Agent Skills 分发、MCP 只读服务和内容后台。可以直接使用 Python + Node.js 在本机运行，无需 Docker；也保留 Docker 部署方式。

## 首版能力

- 9 个递进课程模块、27 篇完整课文，覆盖基础、进阶、专业三个阶段；每篇都包含场景导入、核心概念、跟做任务和课后检查。
- 5 个预置 Wiki 词条，支持中文全文检索、精确短语、分类、标签、难度、更新时间、分页与相关度排序。
- `user` 投稿，`reviewer` / `admin` 审核、驳回、发布、取消发布和置顶；审核历史不可覆盖。
- 公开 MCP 提供 7 个只读工具与对应资源，仅暴露已发布内容；管理员可通过独立的凭证端点调用受后台开关控制的写入工具。
- Agent Skills ZIP 校验、稳定下载地址、原始 `SKILL.md` 与 SHA-256。
- Vue 3 管理后台，覆盖审核、用户角色、Wiki、Skills、MCP、OAuth 凭据、OpenAI 兼容 AI API 与审计日志；配置完成后块编辑器提供浮动 AI 助手和块内 AI 编辑。
- 统一文档站账户中心：个人资料、文件头像、账号安全、MCP 凭据、我的项目和通知。
- GitHub/Gitee 官方 OAuth 绑定；管理员可在后台配置 OAuth Client ID/Secret。

当前仍不包含评论、点赞、收藏、举报和邮件找回密码；通知目前聚合投稿状态变化。

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

## 本地运行（无需 Docker）

后端要求 Python 3.13。以下命令从项目根目录开始，使用同一个虚拟环境完成安装、迁移、初始化和启动；已有 `.venv` 时可跳过创建与安装：

```powershell
cd 开发/backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app.seed
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端要求 Node.js 22 或更新版本。在另一个终端从项目根目录启动。已有 `node_modules` 时可跳过安装；首次安装使用锁定依赖：

```powershell
cd 开发/frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

访问网站 [http://localhost:5173](http://localhost:5173)，API 文档在 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)，公开 MCP 在 `http://127.0.0.1:8000/mcp`，管理员写入 MCP 在 `http://127.0.0.1:8000/mcp/admin`。前端代理 API、MCP 和 Skill 文件下载，`/skills` 本身仍是网页路由，可直接打开与刷新。

全新数据库的本地管理员为 `admin@example.com` / `ChangeMe123!`。如果已存在管理员，初始化不会覆盖其密码。数据保存在 `开发/backend/data/vibecodingwiki.db`，重启不会清空。头像文件位于 `VCW_DATA_DIR/media/avatars`。后端 `.env` 或 `VCW_` 环境变量可以覆盖配置，根目录 Docker `.env` 不会自动被本地后端读取。

开发、构建和测试显式使用 TypeScript 配置，避免历史生成的同名 `.js` 文件被工具优先加载。端口被占用时会报错，不会悄悄切换到另一个端口。

测试命令（分别在对应目录运行）：

```powershell
cd 开发/backend
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m pytest -q

# 在另一个终端从项目根目录开始
cd 开发/frontend
npm test
npm run build
npm run test:e2e
npm run test:integration
```

课程正文保存在 `开发/backend/app/course_content.py`，按基础、进阶、专业三个阶段的九个公开模块、每模块三篇课文组织；内容同时面向零基础学习者、计算机专业学生和工程师。每篇统一采用“场景导入—核心概念—跟做任务—课后检查”的叙事结构，并在正文末尾生成学习目标、实践任务和完成标准卡片。首次改版会自动用于全新数据库；已有开发库请先备份，再运行：

```powershell
cd 开发/backend
.venv/Scripts/python.exe ../../tools/refresh_course_content.py --database data/vibecodingwiki.db
```

知识库编辑器使用 `开发/frontend/vendor/my-notebook-vue-block-editor-0.1.0.tgz` 的本机打包依赖，来源为本机 `vue-block-editor` 最新构建；安装锁文件、归档 SHA-256 和依赖路径均已固定。前端依赖安装后可运行 `npm run verify:editor-package` 检查归档未被替换。

`test:e2e` 使用接口模拟检查界面；`test:integration` 自动启动真实后端（8001）与前端（5174），使用 `.local/integration-*` 独立数据库验证注册、投稿审核、后台管理和下载，不修改日常使用数据库。首次运行浏览器测试若缺少浏览器，执行 `npx playwright install chromium`。测试详情见 [本地验收记录](文档/LOCAL_VERIFICATION.md)。

## 目录

```text
开发/frontend/   Vue 3 + TypeScript + Vite
开发/backend/    FastAPI + SQLAlchemy + Alembic + SQLite
文档/            填写版需求报告、周报、开题 PPT 与绘图清单
.github/         CI、Issue 与 PR 模板
```

规划、需求、架构和接口分别见 [PROJECT_PLAN.md](PROJECT_PLAN.md)、[REQUIREMENTS.md](REQUIREMENTS.md)、[ARCHITECTURE.md](ARCHITECTURE.md) 和 [API_CONTRACT.md](API_CONTRACT.md)。贡献与安全要求见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

## MCP 与 Skills

MCP 目标规范为 `2026-07-28`。公开工具：`search_wiki`、`get_wiki_article`、`list_wiki_categories`、`list_courses`、`get_lesson`、`list_projects`、`list_skills`。服务不会返回草稿、投稿人资料或后台数据。

管理员可在后台的“MCP 管理”中生成全局令牌，或在管理员账户的安全设置中生成个人 MCP 凭据；将 `Authorization: Bearer <令牌>` 加到管理员端点的请求头，即可发现并调用 `update_wiki_article`、`update_lesson` 和 `update_course`。该端点始终要求管理员令牌，更新会记录为 `wiki.update.mcp` 审计事件；令牌只保存 SHA-256 摘要，不会在接口响应中回显。公开 MCP 的“开启令牌鉴权”开关只影响 `/mcp`，管理员写入端点不会因该开关关闭而失去保护。

管理员 MCP 也支持知识库维护：`create_wiki_article`、`delete_wiki_article`、`move_wiki_article`，以及知识库分类的 `create_wiki_category`、`update_wiki_category`、`delete_wiki_category`。这些操作都要求同一管理员 Bearer 凭证，并分别写入 MCP 审计事件；删除分类会同时删除其子分类和词条。

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

## 后台基本操作

登录管理员账号后进入 `/admin`：

- 审核：按状态查看投稿、展开完整说明，通过或填写原因驳回；已发布项目可取消发布、设置或取消推荐。
- 用户：调整角色、启用或停用账号；禁止停用自己或移除自己的管理员角色，停用时撤销刷新令牌。账号区支持管理员修改自己的密码。
- Wiki：查看草稿与已发布内容，新建或编辑词条，通过状态选择发布或撤回草稿。
- Skills：上传 ZIP 时选择草稿或发布，管理已有版本的上下架。
- 审计：查看管理操作记录。reviewer 仅显示审核入口，服务端同时校验权限。

投稿页支持独立保存草稿和保存后提交审核。API 校验错误会显示字段及原因。

若本机 pnpm 启动器不可用且依赖已安装，可使用 `npm run dev`、`npm run test`、`npm run build`；浏览器测试可先启动开发服务，再设置 `PLAYWRIGHT_BASE_URL=http://localhost:5173` 后执行 `npm run test:e2e`。

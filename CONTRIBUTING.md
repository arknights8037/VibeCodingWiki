# 贡献指南

## 分支与提交

日常开发从 `develop` 创建 `feat/<topic>` 或 `fix/<topic>`。`main` 只接收评审后的 PR，仓库管理员应开启 required checks、至少一名 reviewer、禁止 force push 和删除保护分支。

提交使用 Conventional Commits，例如 `feat(wiki): add phrase filtering`、`fix(auth): rotate refresh token`、`docs(course): revise module four`。请保持一次提交只做一个可解释变更，并用自己的 GitHub 账号提交实际负责内容。

## 本地门禁

```text
backend: ruff check . && pytest && alembic upgrade head
frontend: pnpm test && pnpm build
integration: pnpm test:e2e && docker compose build
```

PR 需说明目的、测试证据、数据库迁移、截图（UI 变更）、内容来源/版本和安全影响。不要提交 `.env`、数据库、令牌、真实学生资料或未授权素材。

## 内容与项目审核

- 新课程/Wiki 应给出学习目标、适用版本、可复现实例与风险边界。
- 不把 AI 输出当事实来源；命令和代码须人工运行验证。
- 投稿仓库必须公开可访问、明确许可证、无恶意脚本或敏感信息。
- 审核本人投稿属于利益冲突，系统禁止； reviewer 应写清通过依据或可执行的驳回意见。

## 数据库变更

修改模型时新增 Alembic revision，不编辑已发布 revision。升级和空库初始化都要验证；FTS5 结构变化需附重建与回滚说明。

## 变更目的

<!-- 关联 Issue，并说明用户可观察到的结果。 -->

## 验证证据

- [ ] 后端 `ruff check .` 与 `pytest`
- [ ] 前端 `pnpm test` 与 `pnpm build`
- [ ] 涉及关键流程时运行 Playwright
- [ ] 涉及迁移时验证空库 `alembic upgrade head`
- [ ] UI 变更附截图；内容变更标注来源和适用版本

## 风险检查

- [ ] 没有提交密钥、数据库、真实个人资料或敏感日志
- [ ] 已检查 RBAC、CSRF、Markdown/ZIP 输入和发布态过滤
- [ ] 已说明回滚方式和范围外事项

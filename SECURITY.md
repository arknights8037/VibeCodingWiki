# 安全策略

## 报告漏洞

请不要在公开 Issue 中披露可利用细节。仓库上线后由维护者在 GitHub Security Advisories 中启用私密报告；启用前请联系项目负责人（联系方式待团队填写）。报告应包含影响版本、复现步骤、预期/实际结果和最小化证明。维护者目标是在 3 个工作日内确认收到，在 10 个工作日内给出处置计划。

## 支持范围

课程首版 `0.1.x` 在发布期间接受安全修复；未发布分支和自行修改部署不承诺支持。不要将演示默认密钥和管理员密码用于公开环境。

## 关键控制

- Argon2 密码哈希；短期 JWT；刷新令牌轮换、哈希存储、可撤销。
- HttpOnly/SameSite Cookie；写请求 CSRF；生产环境使用 HTTPS 与 Secure Cookie。
- API 端 RBAC、资源所有权与“审核者不是作者”检查。
- Markdown DOMPurify；Skill ZIP 大小、数量、单根 `SKILL.md` 与路径穿越校验；上传脚本永不执行。
- MCP/公开 REST 只暴露 `published`；审计日志不记录令牌、密码或 Cookie。

## 部署清单

设置随机 `VCW_ACCESS_SECRET` 和强管理员密码；设置 `VCW_COOKIE_SECURE=true`；在 TLS 反向代理后运行；限制数据卷权限；备份 SQLite 时使用一致性快照；定期更新镜像和依赖；检查审计日志和异常认证频率。SQLite 首版不得扩成多个后端副本。

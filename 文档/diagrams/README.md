# 人工绘图清单

课程要求的用例图、顺序图和活动图由项目组使用绘图工具人工完成。请保留可编辑源文件、导出 PNG/SVG、作者姓名与评审日期；不得将自动生成图标为人工成果。

## 1. 用例图

- 参与者：访客、user、reviewer、admin、MCP Client。
- 用例：课程学习、Wiki 查询、查看公开项目、记录进度、投稿/重投、审核、用户/内容/Skill 管理、调用只读工具。
- 边界：公开读取与后台写入分开；reviewer 不能审核自己的投稿。

## 2. 顺序图

- lifeline：用户浏览器、Nginx、FastAPI 鉴权/CSRF、Project Service、SQLite、reviewer。
- 主流程：保存草稿 → 提交 → 待审 → reviewer 通过 → 更新 published → 新增 ReviewEvent/AuditLog。
- 分支：CSRF 失败、越权、自审、驳回后重投、取消发布。

## 3. 活动图

- 输入：q、phrase、category、tags、difficulty、updated_after、sort、page。
- 节点：参数校验 → 安全生成 FTS 查询 → 分类/标签过滤 → 排序 → 分页。
- 分支：空关键词、非法特殊字符、无结果、页码越界。

完成后将源文件与导出图放在本目录，并在需求报告相应占位处插入人工成果。

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "SchoolDOC"
OUTPUT = ROOT / "文档"


def clear_body(document: Document) -> None:
    body = document._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def set_cell_shading(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    shading = props.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        props.append(shading)
    shading.set(qn("w:fill"), fill)


def prevent_row_splitting(table) -> None:
    for row in table.rows:
        props = row._tr.get_or_add_trPr()
        if props.find(qn("w:cantSplit")) is None:
            props.append(OxmlElement("w:cantSplit"))


def set_doc_style(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    normal = document.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.35
    if "Title" not in document.styles:
        document.styles.add_style("Title", WD_STYLE_TYPE.PARAGRAPH)
    for list_style in ("List Bullet", "List Number"):
        if list_style not in document.styles:
            style = document.styles.add_style(list_style, WD_STYLE_TYPE.PARAGRAPH)
            style.base_style = normal
            style.paragraph_format.left_indent = Cm(0.7)
            style.paragraph_format.first_line_indent = Cm(-0.35)
    for name, size, color in (("Title", 26, "173B3F"), ("Heading 1", 17, "173B3F"), ("Heading 2", 13, "1F6F78")):
        style = document.styles[name]
        style.font.name = "Microsoft YaHei"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")


def add_title(document: Document, title: str, subtitle: str) -> None:
    p = document.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(title)
    p2 = document.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p2.add_run(subtitle)
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor.from_string("547276")
    document.add_paragraph()
    table = document.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    for row, (left, right) in zip(table.rows, [
        ("项目名称", "VibeCodingWiki"),
        ("版本", "课程交付版 v0.1"),
        ("团队", "班级 / 小组 / 成员：待团队填写"),
        ("日期", "2026 年 9 月"),
    ]):
        row.cells[0].text, row.cells[1].text = left, right
        set_cell_shading(row.cells[0], "DDEDEE")
    document.add_page_break()


def add_bullets(document: Document, items: list[str]) -> None:
    for item in items:
        document.add_paragraph(item, style="List Bullet")


def add_requirement_doc() -> None:
    source = SOURCE / "文档模板1-软件需求构思及描述模板.docx"
    document = Document(source)
    clear_body(document)
    set_doc_style(document)
    add_title(document, "VibeCodingWiki 软件需求构思及描述", "基于 Vue 3、FastAPI、SQLite 与开放 Agent 生态的中文学习平台")

    sections = [
        ("1. 项目背景", [
            "生成式 AI 正在降低应用开发的起步门槛，但零基础学习者常把“能生成代码”误当作“能交付软件”。现有资料分散在视频、博客、产品文档和社区帖子中，缺少从问题定义到部署维护的连续路径，也缺少对安全、测试、版权与人工审查的系统说明。",
            "VibeCodingWiki 将标准文档式课程、可筛选 Wiki、经审核的开源项目、MCP 只读知识服务与 Agent Skills 分发集中到一个课程级单机平台。其价值不在于替用户跳过工程过程，而在于把每次生成变成可描述、可验证、可追踪的迭代。",
        ]),
        ("2. 问题描述", [
            "目标用户面临四类问题：概念门槛高；提示、上下文与工程规范相互割裂；生成结果缺少测试和安全复核；优秀项目与技能包缺少稳定、可信的发现渠道。教师或小组还需要可审核、可复现的项目过程，而不是只有一份不可解释的最终代码。",
            "系统应以“读得懂—找得到—做得出—验得过”为主线：课程解释方法，Wiki 解决即时查询，项目广场提供真实参考，审核与审计保证公开内容边界，MCP/Skills 让知识被其他智能体以标准方式调用。",
        ]),
        ("3. 创意说明", [
            "本方案的核心创意是把教学内容和开放接口放在同一发布状态模型下。网页、REST 与 MCP 读取同一份发布数据，避免面向人和面向智能体的知识不一致；Skills 采用稳定 URL 与确定性 ZIP，使安装说明、版本和校验值可以复核。",
            "课程聚焦五个核心模块：风险认知、需求拆解、提示词与上下文、环境与 Git、测试与调试。每个模块都包含实践和完成标准。",
        ]),
        ("4. 竞品与差异", [
            "通用文档站擅长准确参考但学习路径分散；视频课程具备叙事性但查询和版本维护较弱；开源导航站便于发现项目却通常缺少教学上下文与审核闭环；通用 AI 助手能即时回答，但答案版本、来源和复用方式不稳定。",
            "VibeCodingWiki 的差异是：中文零基础路径与高级查询并存；公开项目必须经过角色化审核；网页和 MCP 严格共享发布边界；Skills 只校验和分发而不执行；单机 Compose 可在课程环境低成本复现。",
        ]),
        ("5. 系统组成和部署", [
            "浏览器访问 Nginx 统一入口。Nginx 托管 Vue 静态资源并反向代理 /api、/mcp 和 /skills。FastAPI 提供 REST、RBAC、CSRF、FTS5 搜索、Skill 校验与 MCP 会话管理；SQLAlchemy/Alembic 管理 SQLite。数据、上传与技能包位于命名卷。",
            "SQLite 启用 WAL、外键与 5 秒 busy timeout，后端固定一个 Uvicorn worker。首版不引入 PostgreSQL、Redis、对象存储或队列；需要横向扩容时先迁移数据库。验收入口为 http://localhost。",
        ]),
    ]
    for heading, paragraphs in sections:
        document.add_heading(heading, level=1)
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)

    document.add_page_break()
    document.add_heading("6. 功能需求", level=1)
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["编号", "功能", "关键规则", "优先级"]
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = text
        set_cell_shading(cell, "BFE7DD")
    rows = [
        ("F-01", "课程路径", "9 模块，分基础、进阶、专业三个阶段；目标、前置、正文、实践、完成标准", "Must"),
        ("F-02", "Wiki 高级查询", "全文/短语/分类/标签/难度/时间/分页/排序", "Must"),
        ("F-03", "身份与进度", "Argon2；访问与可撤销刷新 Cookie；CSRF", "Must"),
        ("F-04", "项目投稿", "草稿—待审—发布/驳回；驳回可重投", "Must"),
        ("F-05", "审核后台", "reviewer 不审本人；admin 管用户/内容/审计", "Must"),
        ("F-06", "Skills 分发", "结构/路径/体积校验；SHA-256；从不执行脚本", "Must"),
        ("F-07", "MCP 服务", "6 个只读工具；仅 published；2026-07-28", "Must"),
        ("F-08", "互动社区", "评论、点赞、收藏、举报、通知", "Won't v1"),
    ]
    for values in rows:
        for cell, value in zip(table.add_row().cells, values):
            cell.text = value
    prevent_row_splitting(table)

    document.add_heading("6.1 角色和用例", level=2)
    add_bullets(document, [
        "访客：浏览发布课程、Wiki、项目和 Skills，调用公开 MCP。",
        "注册用户：记录课文进度，创建/编辑自己的投稿并提交审核。",
        "reviewer：审核他人投稿、驳回、发布、取消发布和设置推荐。",
        "admin：管理全部内容、用户角色、Skills 和审计日志。",
    ])
    document.add_heading("6.2 业务规则", level=2)
    add_bullets(document, [
        "投稿状态固定为 draft → pending_review → published/rejected；驳回后可编辑并重投。",
        "所有审核动作追加 ReviewEvent 和 AuditLog，不覆盖历史；作者不能审核本人投稿。",
        "访问令牌短期有效，刷新令牌仅存哈希并在每次刷新时轮换；写操作校验 CSRF。",
        "MCP 与公共 REST 只能读取 published 内容，不返回草稿、投稿人信息和后台数据。",
        "Skill ZIP 最大 5 MB、最多 100 文件、恰好一个合法 SKILL.md；拒绝绝对路径和路径穿越。",
    ])

    document.add_heading("7. 课程与首批内容", level=1)
    modules = [
        "Vibe Coding 基本概念与风险", "问题定义和需求拆解", "提示词、上下文和规范驱动开发",
        "开发环境、终端与 Git",
        "测试、调试、安全和人工审查",
    ]
    for index, module in enumerate(modules, 1):
        document.add_paragraph(f"模块 {index}　{module}", style="List Number")
    document.add_paragraph("每个模块均提供完整示例课文；首批 Wiki 保留 Vibe Coding、AI Coding、工程提示、上下文窗口和 Git 五个核心词条。")

    document.add_heading("8. 非功能需求", level=1)
    add_bullets(document, [
        "部署：新环境一条 Compose 命令启动；容器重启后数据库和文件仍存在。",
        "质量：pytest、Vitest、Playwright、前后端构建、迁移和 Docker 镜像构建作为门禁。",
        "性能：列表分页；参数长度受限；课程级规模下常规查询应在可交互时间内返回。",
        "安全：最小权限、参数绑定、Markdown 清理、ZIP 防穿越、密码/令牌不入日志。",
        "可维护性：类型化契约、Alembic 迁移、Conventional Commits 和 PR 审核。",
        "可访问性：键盘可操作、正文宽度受控、移动端可读、状态不只依赖颜色表达。",
    ])

    document.add_heading("9. 分析模型说明与人工绘图占位", level=1)
    document.add_paragraph("课程要求的 UML 成果必须由项目组使用绘图工具人工完成。以下只给出绘制输入和检查清单，不生成或冒充人工 UML 原图。")
    uml = document.add_table(rows=1, cols=3)
    uml.style = "Table Grid"
    for cell, text in zip(uml.rows[0].cells, ["图", "应包含内容", "完成状态"]):
        cell.text = text
        set_cell_shading(cell, "FFE29A")
    for values in [
        ("用例图", "访客/user/reviewer/admin；学习、查询、投稿、审核、管理、MCP", "待人工绘制"),
        ("顺序图", "提交→鉴权/CSRF→待审→审核→状态/ReviewEvent/AuditLog", "待人工绘制"),
        ("活动图", "查询校验→FTS/筛选→排序→分页→空结果/结果", "待人工绘制"),
    ]:
        for cell, value in zip(uml.add_row().cells, values):
            cell.text = value
    prevent_row_splitting(uml)

    document.add_heading("10. 可行性分析", level=1)
    document.add_paragraph("技术上，核心框架均成熟且有自动化测试支持；经济上依赖均为开源，单机资源需求低；操作上通过统一入口和种子数据减少部署步骤；进度上按五周拆分，每周都有可演示增量。SQLite 与中文 FTS 的限制已明确，不把课程部署假设外推到高并发生产系统。")

    document.add_page_break()
    document.add_heading("11. 风险与缓解", level=1)
    risks = document.add_table(rows=1, cols=3)
    risks.style = "Table Grid"
    for cell, text in zip(risks.rows[0].cells, ["风险", "等级", "缓解措施"]):
        cell.text = text
        set_cell_shading(cell, "DDEDEE")
    for values in [
        ("AI 生成代码缺陷或幻觉", "高", "小步变更、自动测试、人工评审、来源和版本记录"),
        ("越权或敏感数据泄露", "高", "后/前台双重边界、发布态过滤、负向测试、审计"),
        ("恶意 ZIP 或脚本", "高", "严格校验、确定性重建、仅分发不执行"),
        ("SQLite 写锁", "中", "WAL、busy timeout、单实例、升级阈值"),
        ("标准版本变化", "中", "锁定 SDK 主版本并使用官方客户端集成测试"),
        ("团队信息或贡献失真", "中", "保留空表，由本人账号提交并由团队确认比例"),
    ]:
        for cell, value in zip(risks.add_row().cells, values):
            cell.text = value
    prevent_row_splitting(risks)

    document.add_heading("12. 验收标准与范围边界", level=1)
    add_bullets(document, [
        "访客只能读发布内容；普通用户不能访问后台；reviewer 不能审核本人投稿。",
        "中文关键词、短语、多标签、特殊字符、分页、空结果均有测试，不能注入 SQL/FTS。",
        "6 个 MCP 工具可发现并调用，内容与 REST 发布数据一致。",
        "下载 Skill 可解压，原始 SKILL.md、版本、URL 和 SHA-256 一致。",
        "首版不含评论、点赞、收藏、举报、通知、OAuth 和邮件找回密码。",
    ])
    document.add_paragraph("未核验事项一律标为计划或待确认；真实团队身份、贡献比例、GitHub 远程地址、域名与人工 UML 由项目组补录。")
    document.save(OUTPUT / "VibeCodingWiki软件需求构思及描述.docx")


def add_weekly_doc() -> None:
    source = SOURCE / "文档模板2-小组周总结（每周添加内容）.docx"
    document = Document(source)
    clear_body(document)
    set_doc_style(document)
    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("X班 X小组周总结报告")
    document.add_paragraph("班级、小组、姓名、学号、平台账号、分工和贡献比例均由团队成员本人补录；本文件不虚构个人信息。")

    info = document.add_table(rows=4, cols=2)
    info.style = "Table Grid"
    for row, values in zip(info.rows, [
        ("班级 / 小组", "待填写"), ("组长姓名", "待填写"),
        ("成员姓名", "待填写"), ("统计周期", "第 1 周（日期待填写）"),
    ]):
        row.cells[0].text, row.cells[1].text = values
        set_cell_shading(row.cells[0], "DDEDEE")

    document.add_heading("分工及贡献记录（每周追加）", level=1)
    team = document.add_table(rows=5, cols=6)
    team.style = "Table Grid"
    headers = ["姓名", "学号 / 班级", "平台账号", "分工", "对应提交/PR", "贡献比例"]
    for cell, text in zip(team.rows[0].cells, headers):
        cell.text = text
        set_cell_shading(cell, "BFE7DD")
    for row in team.rows[1:]:
        for cell in row.cells:
            cell.text = "待本人填写"
    prevent_row_splitting(team)

    document.add_heading("第 1 周总结报告", level=1)
    document.add_heading("本周目标", level=2)
    add_bullets(document, [
        "明确 VibeCodingWiki 的用户、范围、角色和审核状态机。",
        "确定 Vue 3 + TypeScript / FastAPI / SQLite / Docker Compose 技术路线。",
        "完成可运行工程骨架、9 模块课程与 5 个 Wiki 种子内容。",
        "形成需求、架构、接口、安全、贡献规范以及课程汇报制品。",
    ])
    document.add_heading("本周已生成制品（需团队复核后认领）", level=2)
    add_bullets(document, [
        "前端页面：课程、Wiki 高级查询、项目广场/投稿、Skills、登录注册、个人记录和后台。",
        "后端能力：SQLite 模型与迁移、FTS5、Cookie/CSRF/RBAC、审核审计、Skills 校验、MCP 只读工具。",
        "工程治理：Compose、环境变量示例、Git 初始化、CI、Issue/PR 模板和 MIT 许可证。",
        "课程制品：填写版需求报告、周报、约 10 页开题汇报；人工 UML 仍待团队完成。",
    ])
    document.add_paragraph("说明：以上仅表示仓库中已生成相应文件，不代表任何具体成员已经完成或认领贡献。实际完成情况以成员本人提交和团队评审记录为准。")

    document.add_heading("问题、风险与调整", level=2)
    add_bullets(document, [
        "课程部署需要兼顾标准先进性与环境可复现性；使用版本范围和集成测试控制 SDK 变化。",
        "SQLite 只适用于单后端实例；文档明确 WAL、busy timeout 和升级边界。",
        "公开投稿与 Skill ZIP 是主要输入风险；首版不执行上传脚本，并补充路径穿越与权限负向测试。",
        "用例图、顺序图和活动图按课程要求留作人工绘制，不使用自动生成图冒充成果。",
    ])

    document.add_page_break()
    document.add_heading("下周计划", level=2)
    next_week = document.add_table(rows=1, cols=4)
    next_week.style = "Table Grid"
    for cell, text in zip(next_week.rows[0].cells, ["任务", "负责人", "完成判据", "状态"]):
        cell.text = text
        set_cell_shading(cell, "FFE29A")
    for values in [
        ("复核课程与 Wiki", "待填写", "术语、链接、难度和课后任务逐项确认", "计划"),
        ("补绘 3 张 UML", "待团队填写", "源文件+导出图+评审记录齐全", "计划"),
        ("真实浏览器 E2E", "待填写", "访客、投稿、审核关键流程通过", "计划"),
        ("演示彩排", "待填写", "10 分钟内完成启动、检索、审核、MCP 演示", "计划"),
    ]:
        for cell, value in zip(next_week.add_row().cells, values):
            cell.text = value
    prevent_row_splitting(next_week)

    document.add_heading("AI 工具使用说明", level=2)
    document.add_paragraph("工具：OpenAI Codex（具体模型版本由团队补录）。使用范围：需求拆解、工程骨架、示例课文、测试与文档初稿。典型流程：输入项目范围和验收条件 → 生成小步实现 → 本地 lint/test/build → 人工检查安全边界和内容准确性 → 保留问题与修订记录。")
    document.add_paragraph("反思：AI 擅长并行生成结构化初稿，但会出现名称不一致、版本差异、格式溢出和过度自信。团队必须核对官方规范、运行测试、审阅差异，并由成员本人对最终提交负责。不得把 AI 生成的 UML 标为人工绘图。")

    document.add_page_break()
    document.add_heading("签字与确认", level=2)
    sign = document.add_table(rows=3, cols=2)
    sign.style = "Table Grid"
    for row, values in zip(sign.rows, [("组长确认", "待填写"), ("成员确认", "待填写"), ("教师反馈", "待填写")]):
        row.cells[0].text, row.cells[1].text = values
    document.save(OUTPUT / "VibeCodingWiki小组周总结.docx")


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    add_requirement_doc()
    add_weekly_doc()

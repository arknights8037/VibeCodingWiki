# Retired seed content is archived on existing installations.
from app.course_content import COURSES as COURSE_CONTENT

COURSES = COURSE_CONTENT

RETIRED_COURSE_SLUGS = ("docker-operations", "fastapi-sqlite", "mcp-agent-skills", "vue-typescript")
RETIRED_WIKI_SLUGS = (
    "conventional-commits",
    "vue-3",
    "typescript",
    "pinia",
    "fastapi",
    "rest-api",
    "pydantic",
    "sqlalchemy",
    "sqlite",
    "fts5",
    "docker",
    "docker-compose",
    "csrf",
    "mcp",
    "agent-skills",
)
WIKI = [
    (
        "vibe-coding",
        "Vibe Coding",
        "AI Coding",
        "通过自然语言与编程模型协作生成、修改和验证代码的开发方式。",
        "Vibe Coding 以短反馈循环推进：描述目标、生成小改动、运行验证、人工审查。它适合原型和重复性工作，但最终质量责任仍由开发者承担。",
        "beginner",
        ["ai", "workflow"],
    ),
    (
        "ai-coding",
        "AI Coding",
        "AI Coding",
        "使用生成式模型辅助分析、编码、测试和文档工作的总称。",
        "AI Coding 可以解释代码、生成测试和提出修改。模型输出属于候选方案，必须结合项目上下文、运行结果和人工判断确认。",
        "beginner",
        ["ai", "review"],
    ),
    (
        "prompt-engineering",
        "工程提示",
        "AI Coding",
        "为编码任务提供背景、目标、约束和验收方法。",
        "工程提示应指出相关文件、预期行为、兼容边界和验证命令。减少无关角色设定，保持每次任务范围清晰。",
        "beginner",
        ["ai", "spec"],
    ),
    (
        "context-window",
        "上下文窗口",
        "AI Coding",
        "模型一次请求中能够处理的信息范围。",
        "上下文包括对话、代码、文档和工具输出。只提供相关材料能降低噪声；长期规则应写入仓库文档，而不是依赖模型记忆。",
        "intermediate",
        ["ai", "context"],
    ),
    (
        "git",
        "Git",
        "工程工具",
        "记录文件历史并支持分支协作的分布式版本控制系统。",
        "Git 使用提交保存可追踪变更。课程项目应让每名成员使用自己的账号提交对应成果，并通过分支和合并请求完成协作。",
        "beginner",
        ["git", "collaboration"],
    ),
]

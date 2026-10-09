"""The single source of truth for MCP tools and resources exposed by the app."""

PUBLIC_MCP_TOOLS = {
    "search_wiki": "搜索已发布的 Wiki 文章",
    "get_wiki_article": "读取 Wiki 文章全文",
    "list_wiki_categories": "列出包含已发布词条的 Wiki 分类",
    "list_courses": "列出已发布课程",
    "get_lesson": "读取课程课文",
    "list_projects": "列出已发布开源项目",
    "list_skills": "列出已发布 Agent Skills",
}

ADMIN_MCP_TOOLS = {
    "update_wiki_article": "修改 Wiki 词条",
    "create_wiki_article": "创建 Wiki 词条",
    "delete_wiki_article": "删除 Wiki 词条",
    "move_wiki_article": "调整 Wiki 词条顺序",
    "create_wiki_category": "创建 Wiki 分类",
    "update_wiki_category": "修改 Wiki 分类",
    "delete_wiki_category": "删除 Wiki 分类及其内容",
    "update_lesson": "修改课程课文",
    "update_course": "修改课程信息",
}

MCP_TOOL_CATALOG = {**PUBLIC_MCP_TOOLS, **ADMIN_MCP_TOOLS}
MCP_TOOL_SCOPE = {
    **{name: "public" for name in PUBLIC_MCP_TOOLS},
    **{name: "admin" for name in ADMIN_MCP_TOOLS},
}

MCP_RESOURCE_CATALOG = (
    {
        "uri": "wiki://articles/{slug}",
        "description": "以 Markdown 读取已发布的 Wiki 词条",
        "scope": "public",
        "endpoint": "/mcp",
    },
    {
        "uri": "course://lessons/{slug}",
        "description": "以 Markdown 读取已发布的课程课文",
        "scope": "public",
        "endpoint": "/mcp",
    },
)

import hashlib
import json
from types import SimpleNamespace

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import select

from app.database import SessionLocal
from app.mcp_server import admin_mcp, mcp
from app.models import Lesson, MCPSettings, MCPToolSetting, WikiArticle


@pytest.mark.asyncio
async def test_mcp_discovers_read_only_tools():
    async with Client(mcp, mode="2026-07-28") as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        assert names == {
            "search_wiki",
            "get_wiki_article",
            "list_wiki_categories",
            "list_courses",
            "get_lesson",
            "list_projects",
            "list_skills",
        }
        courses = await client.call_tool("list_courses")
        assert not courses.is_error


@pytest.mark.asyncio
async def test_mcp_tool_switch_controls_discovery_and_calls():
    async with SessionLocal() as session:
        session.add(MCPToolSetting(name="list_courses", description="", enabled=False))
        await session.commit()

    async with Client(mcp, mode="2026-07-28") as client:
        result = await client.list_tools()
        assert "list_courses" not in {tool.name for tool in result.tools}

    with pytest.raises(ToolError, match="MCP 工具已停用"):
        await mcp.call_tool("list_courses", {})


@pytest.mark.asyncio
@pytest.mark.parametrize('tool_name,model', [('update_wiki_article', WikiArticle), ('update_lesson', Lesson)])
@pytest.mark.parametrize('as_string', [True, False])
async def test_admin_tool_preserves_structured_json(tool_name, model, as_string):
    token = 'isolated-mcp-test-admin'
    async with SessionLocal() as session:
        row = await session.get(MCPSettings, 1)
        if row is None:
            row = MCPSettings(id=1)
            session.add(row)
        row.auth_token_hash = hashlib.sha256(token.encode()).hexdigest()
        item = await session.scalar(select(model).order_by(model.id))
        slug, title = item.slug, item.title
        await session.commit()
    doc = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': '保存加粗格式', 'marks': [{'type': 'bold'}]}]}]}
    # Exercise SDK argument preprocessing: optional JSON strings become dicts.
    ctx = SimpleNamespace(headers={'Authorization': f'Bearer {token}'})
    result = await admin_mcp.call_tool(tool_name, {
        'slug': slug, 'body_markdown': '管理员保存的正文测试，确保结构化内容和文字格式不会丢失。',
        'content_json': json.dumps(doc) if as_string else doc,
    }, context=ctx)
    assert not getattr(result, 'is_error', False)
    async with SessionLocal() as session:
        saved = await session.scalar(select(model).where(model.slug == slug))
        assert saved.title == title
        assert json.loads(saved.content_json)['content'] == doc['content']
        assert saved.body_markdown.startswith('管理员保存')

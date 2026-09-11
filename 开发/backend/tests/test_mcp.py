import pytest
from mcp import Client

from app.mcp_server import mcp


@pytest.mark.asyncio
async def test_mcp_discovers_six_read_only_tools():
    async with Client(mcp, mode="2026-07-28") as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        assert names == {
            "search_wiki",
            "get_wiki_article",
            "list_courses",
            "get_lesson",
            "list_projects",
            "list_skills",
        }
        courses = await client.call_tool("list_courses")
        assert not courses.is_error

import hashlib
import io
import zipfile

import pytest
from sqlalchemy import select, text

from app.database import SessionLocal
from app.mcp_server import get_wiki_article, list_projects, list_skills, search_wiki
from app.models import Category, PublicationStatus, ReviewEvent, WikiArticle


async def login(client, email="admin@example.com", password="AdminPassword123!"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies["csrf_token"]}


async def register(client, email):
    response = await client.post("/api/v1/auth/register", json={
        "email": email, "display_name": "功能测试用户", "password": "StrongPassword123!",
    })
    assert response.status_code == 201
    return response.json()["id"]


def skill_zip(content, extra=None):
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as archive:
        archive.writestr("sample/SKILL.md", content)
        for name, value in (extra or {}).items():
            archive.writestr(name, value)
    return result.getvalue()


async def test_session_refresh_rotation_logout_and_duplicate_registration(client):
    await register(client, "session@example.com")
    duplicate = await client.post("/api/v1/auth/register", json={
        "email": "SESSION@example.com", "display_name": "重复用户", "password": "StrongPassword123!",
    })
    assert duplicate.status_code == 409
    headers = await login(client, "session@example.com", "StrongPassword123!")
    old_refresh = client.cookies["refresh_token"]
    assert (await client.get("/api/v1/auth/me")).json()["email"] == "session@example.com"
    assert (await client.post("/api/v1/auth/refresh")).status_code == 403
    assert (await client.post("/api/v1/auth/refresh", headers=headers)).status_code == 200
    assert client.cookies["refresh_token"] != old_refresh
    headers = {"X-CSRF-Token": client.cookies["csrf_token"]}
    assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    client.cookies.set("refresh_token", old_refresh)
    client.cookies.set("csrf_token", "test")
    assert (await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "test"})).status_code == 401


async def test_project_ownership_reject_resubmit_review_history_and_visibility(client):
    owner_id = await register(client, "owner2@example.com")
    headers = await login(client, "owner2@example.com", "StrongPassword123!")
    payload = {
        "name": "完整流程项目", "slug": "full-workflow", "summary": "完整流程测试项目的有效摘要内容",
        "description_markdown": "完整流程测试项目的详细说明，包含运行方法和用途。",
        "repository_url": "https://example.com/repo", "demo_url": "https://example.com/demo",
    }
    created = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert created.status_code == 201
    project_id = created.json()["id"]
    assert (await client.get("/api/v1/projects/full-workflow")).status_code == 404
    assert (await client.post("/api/v1/projects", json=payload, headers=headers)).status_code == 409
    await register(client, "other@example.com")
    other_headers = await login(client, "other@example.com", "StrongPassword123!")
    assert (await client.put(f"/api/v1/projects/{project_id}", json=payload, headers=other_headers)).status_code == 404
    assert (await client.post(f"/api/v1/projects/{project_id}/submit", headers=other_headers)).status_code == 404
    assert (await client.get("/api/v1/reviews/projects")).status_code == 403
    headers = await login(client, "owner2@example.com", "StrongPassword123!")
    await client.post(f"/api/v1/projects/{project_id}/submit", headers=headers)
    assert (await client.put(f"/api/v1/projects/{project_id}", json=payload, headers=headers)).status_code == 409
    admin_headers = await login(client)
    await client.patch(f"/api/v1/admin/users/{owner_id}/role", json={"role": "reviewer"}, headers=admin_headers)
    headers = await login(client, "owner2@example.com", "StrongPassword123!")
    review_path = f"/api/v1/reviews/projects/{project_id}"
    assert (await client.post(review_path, json={"action": "approve"}, headers=headers)).status_code == 403
    assert (await client.get("/api/v1/admin/wiki")).status_code == 403
    admin_headers = await login(client)
    assert (await client.post(review_path, json={"action": "reject", "comment": "补充说明"}, headers=admin_headers)).status_code == 200
    headers = await login(client, "owner2@example.com", "StrongPassword123!")
    assert (await client.get("/api/v1/projects/mine")).json()[0]["review_note"] == "补充说明"
    assert (await client.put(f"/api/v1/projects/{project_id}", json=payload, headers=headers)).status_code == 200
    assert (await client.post(f"/api/v1/projects/{project_id}/submit", headers=headers)).status_code == 200
    admin_headers = await login(client)
    assert (await client.post(review_path, json={"action": "approve"}, headers=admin_headers)).status_code == 200
    assert (await client.get("/api/v1/projects/full-workflow")).json()["demo_url"] == "https://example.com/demo"
    assert any(item["slug"] == "full-workflow" for item in await list_projects())
    await client.post(review_path, json={"action": "unpublish"}, headers=admin_headers)
    assert not any(item["slug"] == "full-workflow" for item in await list_projects())
    async with SessionLocal() as session:
        rows = list(await session.scalars(select(ReviewEvent).where(ReviewEvent.entity_id == project_id).order_by(ReviewEvent.id)))
        assert [row.action for row in rows] == ["reject", "approve", "unpublish"]


async def test_skill_upload_roundtrip_and_mcp_visibility(client):
    headers = await login(client)
    content = "---\nname: uploaded-skill\ndescription: A skill for roundtrip verification\n---\nSee refs/info.txt.\n"
    archive = skill_zip(content, {"sample/refs/info.txt": "reference content"})
    payload = {"version": "1.2.3", "publish": "true"}
    response = await client.post("/api/v1/admin/skills/upload", data=payload, files={"archive": ("sample.zip", archive)}, headers=headers)
    assert response.status_code == 201, response.text
    downloaded = await client.get("/skills/uploaded-skill/1.2.3/download.zip")
    assert hashlib.sha256(downloaded.content).hexdigest() == response.json()["sha256"]
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as result:
        assert result.read("SKILL.md").decode() == content
        assert result.read("refs/info.txt") == b"reference content"
    assert (await client.get("/skills/uploaded-skill/1.2.3/SKILL.md")).text == content
    assert any(item["slug"] == "uploaded-skill" for item in await list_skills())
    duplicate = await client.post("/api/v1/admin/skills/upload", data=payload, files={"archive": ("sample.zip", archive)}, headers=headers)
    assert duplicate.status_code == 409
    invalid_version = await client.post("/api/v1/admin/skills/upload", data={"version": "../bad"}, files={"archive": ("sample.zip", archive)}, headers=headers)
    assert invalid_version.status_code == 422


@pytest.mark.parametrize("content", [b"\xff\xff", "---\n- one\n- two\n---", "---\nname: [\n---", "---\nname: sample\ndescription: sample\nlicense: []\n---"])
async def test_invalid_skill_metadata_returns_validation_error_not_500(client, content):
    headers = await login(client)
    response = await client.post("/api/v1/admin/skills/upload", data={"version": "1.0.0"}, files={"archive": ("bad.zip", skill_zip(content))}, headers=headers)
    assert response.status_code == 422


async def test_combined_search_and_rank_before_pagination(client):
    async with SessionLocal() as session:
        category = await session.scalar(select(Category).limit(1))
        for index in range(4):
            session.add(WikiArticle(slug=f"rank-{index}", title=f"rankword sample {index}", summary="rankword " * (index + 1), body_markdown="phrase-target rankword " + "filler " * (20 - index * 5), category=category, status=PublicationStatus.published))
        session.add(WikiArticle(slug="hidden-search", title="rankword private", summary="private", body_markdown="private draft", category=category, status=PublicationStatus.draft))
        await session.commit()
        ranked = list((await session.execute(text("SELECT rowid FROM wiki_fts WHERE wiki_fts MATCH 'rankword' ORDER BY bm25(wiki_fts), rowid"))).scalars())
        published = set(await session.scalars(select(WikiArticle.id).where(WikiArticle.status == PublicationStatus.published)))
        ranked = [item for item in ranked if item in published]
    pages = []
    for page in (1, 2):
        result = (await client.get("/api/v1/wiki", params={"q": "rankword", "page": page, "page_size": 2})).json()
        assert result["total"] == 4
        pages.extend(item["id"] for item in result["items"])
    assert pages == ranked
    mismatch = await client.get("/api/v1/wiki", params={"q": "missing-unrelated-term", "phrase": "phrase-target"})
    assert mismatch.json()["total"] == 0
    assert (await client.get("/api/v1/wiki", params={"q": "%"})).json()["total"] == 0
    assert await get_wiki_article("hidden-search") == {"error": "article_not_found"}
    assert all(item["slug"] != "hidden-search" for item in await search_wiki("rankword"))

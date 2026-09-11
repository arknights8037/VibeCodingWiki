import hashlib
import io
import zipfile

import pytest


@pytest.mark.asyncio
async def test_public_content_is_seeded(client):
    courses = await client.get("/api/v1/courses")
    wiki = await client.get("/api/v1/wiki", params={"q": "Git"})
    skills = await client.get("/api/v1/skills")
    assert courses.status_code == 200 and len(courses.json()) == 9
    assert wiki.status_code == 200 and wiki.json()["total"] >= 1
    assert skills.status_code == 200 and skills.json()[0]["slug"] == "safe-wiki-research"


@pytest.mark.asyncio
async def test_registration_login_and_csrf(client):
    payload = {
        "display_name": "测试用户",
        "email": "user@example.com",
        "password": "StrongPassword123!",
    }
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    login = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert login.status_code == 200
    no_csrf = await client.post("/api/v1/projects", json={})
    assert no_csrf.status_code == 403


@pytest.mark.asyncio
async def test_password_policy_and_regular_user_rbac(client):
    weak = await client.post(
        "/api/v1/auth/register",
        json={"display_name": "弱密码", "email": "weak@example.com", "password": "abcdefghij"},
    )
    assert weak.status_code == 422
    user = {
        "display_name": "普通用户",
        "email": "plain@example.com",
        "password": "StrongPassword123!",
    }
    await client.post("/api/v1/auth/register", json=user)
    await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    assert (await client.get("/api/v1/admin/users")).status_code == 403


@pytest.mark.asyncio
async def test_wiki_advanced_filters_and_special_characters(client):
    phrase = await client.get("/api/v1/wiki", params={"phrase": "短反馈循环"})
    assert phrase.status_code == 200
    assert any(item["slug"] == "vibe-coding" for item in phrase.json()["items"])

    tags = await client.get("/api/v1/wiki", params=[("tags", "vue"), ("tags", "frontend")])
    assert tags.status_code == 200
    assert {item["slug"] for item in tags.json()["items"]} == {"vue-3"}

    special = await client.get(
        "/api/v1/wiki", params={"q": '" OR 1=1; DROP TABLE wiki_articles;--'}
    )
    assert special.status_code == 200
    future = await client.get("/api/v1/wiki", params={"updated_after": "2999-01-01T00:00:00Z"})
    assert future.status_code == 200 and future.json()["total"] == 0


@pytest.mark.asyncio
async def test_skill_download_matches_structure(client):
    catalog = (await client.get("/api/v1/skills")).json()
    response = await client.get("/skills/safe-wiki-research/1.0.0/download.zip")
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == catalog[0]["sha256"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "SKILL.md" in archive.namelist()
        assert b"name: safe-wiki-research" in archive.read("SKILL.md")


@pytest.mark.asyncio
async def test_project_review_state_machine(client):
    user = {
        "display_name": "投稿者",
        "email": "owner@example.com",
        "password": "StrongPassword123!",
    }
    await client.post("/api/v1/auth/register", json=user)
    await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    headers = {"X-CSRF-Token": client.cookies["csrf_token"]}
    project = {
        "name": "可审核项目",
        "slug": "reviewable-project",
        "summary": "用于验证完整审核状态机的开源项目。",
        "description_markdown": "# 项目\n\n这是一个能够通过最小字段校验的项目说明。",
        "repository_url": "https://github.com/example/reviewable-project",
        "license_name": "MIT",
        "tech_stack": ["Vue", "FastAPI"],
    }
    created = await client.post("/api/v1/projects", json=project, headers=headers)
    assert created.status_code == 201
    submitted = await client.post(
        f"/api/v1/projects/{created.json()['id']}/submit", headers=headers
    )
    assert submitted.status_code == 200

    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPassword123!"},
    )
    headers = {"X-CSRF-Token": client.cookies["csrf_token"]}
    reviewed = await client.post(
        f"/api/v1/reviews/projects/{created.json()['id']}",
        json={"action": "approve", "comment": "内容与仓库信息已核验。", "featured": True},
        headers=headers,
    )
    assert reviewed.status_code == 200
    published = await client.get("/api/v1/projects")
    assert any(item["slug"] == project["slug"] for item in published.json())

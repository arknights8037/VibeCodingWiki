import hashlib
import json
import re
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import require_roles, verify_csrf
from app.mcp_catalog import MCP_RESOURCE_CATALOG, MCP_TOOL_CATALOG, MCP_TOOL_SCOPE
from app.models import (
    AuditLog,
    Category,
    ContentCategory,
    Course,
    Lesson,
    MCPSettings,
    MCPToolSetting,
    ProjectSubmission,
    PublicationStatus,
    RefreshToken,
    ReviewEvent,
    Role,
    SkillPackage,
    Tag,
    User,
    WikiArticle,
)
from app.schemas import (
    AdminCategoryOut,
    AdminCourseOut,
    AdminSkillOut,
    CategoryWrite,
    ContentStatusUpdate,
    CourseWrite,
    DirectoryMove,
    MCPSettingsOut,
    MCPSettingsWrite,
    MCPToolOut,
    MCPToolUpdate,
    Message,
    OAuthSettingsOut,
    OAuthSettingsWrite,
    RoleUpdate,
    SkillContentUpdate,
    SkillIntroUpdate,
    SkillOut,
    SkillReviewUpdate,
    UserOut,
    UserStatusUpdate,
    WikiDetail,
    WikiMove,
    WikiWrite,
)
from app.services.block_content import normalize_content_json
from app.services.lesson_content import with_legacy_cards
from app.services.skills import SkillValidationError, build_skill_archive, validate_skill_archive

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_roles(Role.admin)


async def write_audit(
    session: AsyncSession,
    actor: User,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail or {}, ensure_ascii=False),
        )
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
) -> list[User]:
    return list(await session.scalars(select(User).order_by(User.created_at.desc())))


@router.patch(
    "/users/{user_id}/status", response_model=UserOut, dependencies=[Depends(verify_csrf)]
)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(409, "不能停用自己的账号")
    user.is_active = payload.is_active
    if not payload.is_active:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
    await write_audit(
        session, admin, "user.status.update", "user", str(user.id), payload.model_dump()
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/wiki", response_model=list[WikiDetail])
async def list_admin_wiki(
    _admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> list[WikiArticle]:
    return list(
        await session.scalars(
            select(WikiArticle)
            .options(selectinload(WikiArticle.category), selectinload(WikiArticle.tags))
            .order_by(
                WikiArticle.category_id, WikiArticle.order_index, WikiArticle.updated_at.desc()
            )
        )
    )


def category_tree(categories: list[Category]) -> list[dict]:
    nodes = {
        item.id: {
            "id": item.id,
            "slug": item.slug,
            "name": item.name,
            "parent_id": item.parent_id,
            "order_index": item.order_index,
            "children": [],
            "article_count": len(item.articles),
        }
        for item in categories
    }
    roots = []
    for item in categories:
        node = nodes[item.id]
        if item.parent_id and item.parent_id in nodes:
            nodes[item.parent_id]["children"].append(node)
        else:
            roots.append(node)

    def sort(items: list[dict]):
        items.sort(key=lambda value: (value["order_index"], value["id"]))
        for value in items:
            sort(value["children"])

    sort(roots)
    return roots


@router.get("/wiki/categories", response_model=list[AdminCategoryOut])
async def list_admin_wiki_categories(
    _admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    categories = list(
        await session.scalars(
            select(Category)
            .options(selectinload(Category.articles))
            .order_by(Category.order_index, Category.id)
        )
    )
    return category_tree(categories)


@router.post(
    "/wiki/categories",
    response_model=AdminCategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_wiki_category(
    payload: CategoryWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    slug = payload.slug or f"category-{uuid.uuid4().hex[:12]}"
    if await session.scalar(
        select(Category.id).where((Category.slug == slug) | (Category.name == payload.name))
    ):
        raise HTTPException(409, "分类标识或名称已存在")
    if payload.parent_id and not await session.get(Category, payload.parent_id):
        raise HTTPException(404, "父级分类不存在")
    category = Category(**payload.model_dump(exclude={"slug"}), slug=slug)
    session.add(category)
    await session.flush()
    await write_audit(
        session,
        admin,
        "wiki.category.create",
        "wiki_category",
        str(category.id),
        payload.model_dump(mode="json"),
    )
    await session.commit()
    return {
        "id": category.id,
        "slug": category.slug,
        "name": category.name,
        "parent_id": category.parent_id,
        "order_index": category.order_index,
        "children": [],
        "article_count": 0,
    }


@router.put(
    "/wiki/categories/{category_id}",
    response_model=AdminCategoryOut,
    dependencies=[Depends(verify_csrf)],
)
async def update_wiki_category(
    category_id: int,
    payload: CategoryWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    category = await session.scalar(
        select(Category).where(Category.id == category_id).options(selectinload(Category.articles))
    )
    if not category:
        raise HTTPException(404, "分类不存在")
    if payload.parent_id == category_id:
        raise HTTPException(422, "分类不能嵌套到自身")
    if payload.parent_id and not await session.get(Category, payload.parent_id):
        raise HTTPException(404, "父级分类不存在")
    all_categories = list(await session.scalars(select(Category)))
    children_by_parent: dict[int | None, list[int]] = {}
    for item in all_categories:
        children_by_parent.setdefault(item.parent_id, []).append(item.id)
    descendants: set[int] = set()
    pending = [category_id]
    while pending:
        current = pending.pop()
        for child_id in children_by_parent.get(current, []):
            descendants.add(child_id)
            pending.append(child_id)
    if payload.parent_id in descendants:
        raise HTTPException(422, "父级分类不能设置为当前分类的子分类")
    slug = payload.slug or category.slug
    duplicate = await session.scalar(
        select(Category.id).where(
            ((Category.slug == slug) | (Category.name == payload.name)),
            Category.id != category_id,
        )
    )
    if duplicate:
        raise HTTPException(409, "分类标识或名称已存在")
    category.slug, category.name, category.parent_id, category.order_index = (
        slug,
        payload.name,
        payload.parent_id,
        payload.order_index,
    )
    await write_audit(
        session,
        admin,
        "wiki.category.update",
        "wiki_category",
        str(category.id),
        payload.model_dump(mode="json"),
    )
    await session.commit()
    return {
        "id": category.id,
        "slug": category.slug,
        "name": category.name,
        "parent_id": category.parent_id,
        "order_index": category.order_index,
        "children": [],
        "article_count": len(category.articles),
    }


@router.post(
    "/wiki/categories/{category_id}/move",
    response_model=Message,
    dependencies=[Depends(verify_csrf)],
)
async def move_wiki_category(
    category_id: int,
    payload: WikiMove,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(404, "分类不存在")
    siblings = list(
        await session.scalars(
            select(Category)
            .where(Category.parent_id == category.parent_id)
            .order_by(Category.order_index, Category.id)
        )
    )
    index = next(i for i, item in enumerate(siblings) if item.id == category_id)
    target = index + payload.offset
    if target < 0 or target >= len(siblings):
        raise HTTPException(409, "已在该级目录边界")
    siblings[index], siblings[target] = siblings[target], siblings[index]
    for position, item in enumerate(siblings):
        item.order_index = position
    await write_audit(
        session,
        admin,
        "wiki.category.move",
        "wiki_category",
        str(category_id),
        payload.model_dump(),
    )
    await session.commit()
    return Message(message="分类顺序已更新")


@router.delete(
    "/wiki/categories/{category_id}", response_model=Message, dependencies=[Depends(verify_csrf)]
)
async def delete_wiki_category(
    category_id: int,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    category = await session.get(Category, category_id)
    if not category:
        raise HTTPException(404, "分类不存在")
    categories = list(await session.scalars(select(Category)))
    children_by_parent: dict[int | None, list[Category]] = {}
    for item in categories:
        children_by_parent.setdefault(item.parent_id, []).append(item)
    descendants: list[Category] = []
    pending = [category]
    while pending:
        item = pending.pop()
        descendants.append(item)
        pending.extend(children_by_parent.get(item.id, []))
    descendant_ids = [item.id for item in descendants]
    article_ids = list(
        await session.scalars(
            select(WikiArticle.id).where(WikiArticle.category_id.in_(descendant_ids))
        )
    )
    if article_ids:
        await session.execute(delete(WikiArticle).where(WikiArticle.id.in_(article_ids)))
    await session.execute(delete(Category).where(Category.id.in_(descendant_ids)))
    await write_audit(
        session,
        admin,
        "wiki.category.delete",
        "wiki_category",
        str(category_id),
        {"category_ids": descendant_ids, "article_ids": article_ids},
    )
    await session.commit()
    return Message(message="分类已删除")


@router.post("/wiki/{article_id}/move", response_model=Message, dependencies=[Depends(verify_csrf)])
async def move_wiki_article(
    article_id: int,
    payload: WikiMove,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    article = await session.get(WikiArticle, article_id)
    if not article:
        raise HTTPException(404, "词条不存在")
    siblings = list(
        await session.scalars(
            select(WikiArticle)
            .where(WikiArticle.category_id == article.category_id)
            .order_by(WikiArticle.order_index, WikiArticle.id)
        )
    )
    index = next(i for i, item in enumerate(siblings) if item.id == article_id)
    target = index + payload.offset
    if target < 0 or target >= len(siblings):
        raise HTTPException(409, "已在该分类边界")
    siblings[index], siblings[target] = siblings[target], siblings[index]
    for position, item in enumerate(siblings):
        item.order_index = position
    await write_audit(session, admin, "wiki.move", "wiki", str(article_id), payload.model_dump())
    await session.commit()
    return Message(message="词条顺序已更新")


@router.get("/skills", response_model=list[AdminSkillOut])
async def list_admin_skills(
    _admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> list[SkillPackage]:
    return list(
        await session.scalars(
            select(SkillPackage)
            .options(selectinload(SkillPackage.content_category))
            .order_by(SkillPackage.id.desc())
        )
    )


@router.get("/skills/{skill_id}/review")
async def skill_review_detail(
    skill_id: int, _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
):
    skill = await session.get(SkillPackage, skill_id)
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    return {
        "skill_md": skill.skill_md,
        "body_markdown": re.sub(r"\A\uFEFF?---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)", "", skill.skill_md),
        "files": list(json.loads(skill.files_json)),
        "sha256": skill.sha256,
    }


@router.patch(
    "/skills/{skill_id}/content", response_model=AdminSkillOut,
    dependencies=[Depends(verify_csrf)],
)
async def update_skill_content(
    skill_id: int,
    payload: SkillContentUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> SkillPackage:
    """Update only the instructions while retaining validated frontmatter/files."""
    skill = await session.get(SkillPackage, skill_id)
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    frontmatter = re.match(r"\A\uFEFF?---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)", skill.skill_md)
    if not frontmatter:
        raise HTTPException(422, "Skill 文件缺少有效的 frontmatter")
    skill_md = f"{frontmatter.group(0).rstrip()}\n\n{payload.body_markdown.strip()}\n"
    try:
        checked = validate_skill_archive(build_skill_archive(skill_md, skill.files_json))
    except SkillValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    skill.skill_md = checked["skill_md"]
    skill.sha256 = checked["sha256"]
    await write_audit(
        session, admin, "skill.content.update", "skill", str(skill.id),
        {"name": skill.name, "version": skill.version},
    )
    await session.commit()
    return await session.scalar(
        select(SkillPackage).options(selectinload(SkillPackage.content_category)).where(SkillPackage.id == skill.id)
    )


@router.get("/skills/{skill_id}/download.zip")
async def review_skill_archive(
    skill_id: int, _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
):
    from fastapi.responses import Response

    from app.services.skills import build_skill_archive

    skill = await session.get(SkillPackage, skill_id)
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    return Response(
        build_skill_archive(skill.skill_md, skill.files_json),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{skill.slug}-{skill.version}.zip"'},
    )


@router.patch(
    "/skills/{skill_id}/status", response_model=AdminSkillOut, dependencies=[Depends(verify_csrf)]
)
async def update_skill_status(
    skill_id: int,
    payload: SkillReviewUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> SkillPackage:
    skill = await session.get(SkillPackage, skill_id)
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    if payload.status == "rejected" and not payload.review_note.strip():
        raise HTTPException(422, "请填写驳回原因")
    if payload.status == "rejected" and skill.status != PublicationStatus.pending_review:
        raise HTTPException(409, "只有待审核 Skill 可以驳回")
    skill.review_note = payload.review_note.strip() or None
    skill.status = PublicationStatus(payload.status)
    await write_audit(
        session, admin, "skill.status.update", "skill", str(skill.id), payload.model_dump()
    )
    await session.commit()
    return await session.scalar(
        select(SkillPackage)
        .options(selectinload(SkillPackage.content_category))
        .where(SkillPackage.id == skill.id)
    )


@router.patch(
    "/skills/{skill_id}/intro", response_model=AdminSkillOut, dependencies=[Depends(verify_csrf)]
)
async def update_skill_intro(
    skill_id: int,
    payload: SkillIntroUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> SkillPackage:
    skill = await session.get(SkillPackage, skill_id)
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    skill.summary = payload.summary.strip()
    await write_audit(
        session,
        admin,
        "skill.intro.update",
        "skill",
        str(skill.id),
        {"name": skill.name, "version": skill.version},
    )
    await session.commit()
    return await session.scalar(
        select(SkillPackage)
        .options(selectinload(SkillPackage.content_category))
        .where(SkillPackage.id == skill.id)
    )


async def ensure_mcp_settings(session: AsyncSession) -> tuple[MCPSettings, list[MCPToolSetting]]:
    settings_row = await session.get(MCPSettings, 1)
    if not settings_row:
        settings_row = MCPSettings(id=1)
        session.add(settings_row)
    tools = list(await session.scalars(select(MCPToolSetting).order_by(MCPToolSetting.id)))
    existing = {tool.name for tool in tools}
    for name, description in MCP_TOOL_CATALOG.items():
        if name not in existing:
            item = MCPToolSetting(name=name, description=description, enabled=True)
            session.add(item)
            tools.append(item)
    await session.commit()
    return settings_row, tools


def mcp_settings_response(row: MCPSettings) -> dict:
    return {
        "enabled": row.enabled,
        "auth_enabled": row.auth_enabled,
        "has_token": bool(row.auth_token_hash),
        "public_endpoint": "/mcp",
        "admin_endpoint": "/mcp/admin",
        "resources": list(MCP_RESOURCE_CATALOG),
    }


@router.get("/mcp/settings", response_model=MCPSettingsOut)
async def get_mcp_settings(
    _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
) -> dict:
    row, _ = await ensure_mcp_settings(session)
    return mcp_settings_response(row)


@router.patch("/mcp/settings", response_model=MCPSettingsOut, dependencies=[Depends(verify_csrf)])
async def update_mcp_settings(
    payload: MCPSettingsWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> dict:
    row, _ = await ensure_mcp_settings(session)
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.auth_enabled is not None:
        row.auth_enabled = payload.auth_enabled
    if payload.token is not None:
        row.auth_token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    await write_audit(
        session,
        admin,
        "mcp.settings.update",
        "mcp",
        "1",
        {
            "enabled": row.enabled,
            "auth_enabled": row.auth_enabled,
            "token_changed": payload.token is not None,
        },
    )
    await session.commit()
    return mcp_settings_response(row)


@router.get("/oauth/settings", response_model=OAuthSettingsOut)
async def get_oauth_settings(
    _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
) -> dict:
    row, _ = await ensure_mcp_settings(session)
    return {
        "github_client_id": row.github_client_id,
        "github_configured": bool(row.github_client_id and row.github_client_secret),
        "gitee_client_id": row.gitee_client_id,
        "gitee_configured": bool(row.gitee_client_id and row.gitee_client_secret),
        "ai_base_url": row.ai_base_url,
        "ai_model": row.ai_model,
        "ai_configured": _ai_configured(row),
        "ai_api_key_configured": bool(row.ai_api_key),
    }


@router.patch(
    "/oauth/settings", response_model=OAuthSettingsOut, dependencies=[Depends(verify_csrf)]
)
async def update_oauth_settings(
    payload: OAuthSettingsWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> dict:
    row, _ = await ensure_mcp_settings(session)
    for field in (
        "github_client_id",
        "github_client_secret",
        "gitee_client_id",
        "gitee_client_secret",
        "ai_base_url",
        "ai_model",
        "ai_api_key",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value.strip() or None)
    await write_audit(
        session,
        admin,
        "oauth.settings.update",
        "oauth",
        "1",
        {
            "github": bool(row.github_client_id and row.github_client_secret),
            "gitee": bool(row.gitee_client_id and row.gitee_client_secret),
            "ai": _ai_configured(row),
        },
    )
    await session.commit()
    return {
        "github_client_id": row.github_client_id,
        "github_configured": bool(row.github_client_id and row.github_client_secret),
        "gitee_client_id": row.gitee_client_id,
        "gitee_configured": bool(row.gitee_client_id and row.gitee_client_secret),
        "ai_base_url": row.ai_base_url,
        "ai_model": row.ai_model,
        "ai_configured": _ai_configured(row),
        "ai_api_key_configured": bool(row.ai_api_key),
    }


def _ai_completion_url(base_url: str) -> str:
    try:
        url = httpx.URL(base_url.strip())
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "AI 模型服务地址无效") from exc
    if url.scheme not in {"http", "https"} or url.username or url.password or url.query or url.fragment:
        raise HTTPException(422, "AI 模型服务地址必须是不含凭证和查询参数的 HTTP(S) 地址")
    path = url.path.rstrip("/")
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return str(url.copy_with(path=path))


def _ai_configured(row: MCPSettings) -> bool:
    if not row.ai_base_url or not row.ai_model:
        return False
    try:
        host = httpx.URL(row.ai_base_url).host
    except (TypeError, ValueError):
        return False
    return bool(row.ai_api_key) or host in {"localhost", "127.0.0.1", "::1"}


@router.post("/ai/completions", dependencies=[Depends(verify_csrf)])
async def ai_completion(
    request: Request,
    _admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> Response:
    row, _ = await ensure_mcp_settings(session)
    if not row.ai_base_url or not row.ai_model or not _ai_configured(row):
        raise HTTPException(409, "请先在第三方绑定中完成 AI API 配置")
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(400, "AI 请求格式无效") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("stream"), bool) or not isinstance(payload.get("messages"), list):
        raise HTTPException(400, "AI 请求必须使用 Chat Completions 格式，并明确指定 stream")
    stream = payload["stream"]
    payload = {**payload, "model": row.ai_model, "stream": stream}
    headers = {
        "Accept": "text/event-stream" if stream else "application/json",
        **({"Authorization": f"Bearer {row.ai_api_key}"} if row.ai_api_key else {}),
    }
    client = httpx.AsyncClient(timeout=60, follow_redirects=False)
    try:
        upstream = await client.send(
            client.build_request("POST", _ai_completion_url(row.ai_base_url), json=payload, headers=headers),
            stream=stream,
        )
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(502, "无法连接 AI 模型服务，请检查地址和网络") from exc
    if not stream:
        try:
            content = await upstream.aread()
        finally:
            await upstream.aclose()
            await client.aclose()
        return Response(content=content, status_code=upstream.status_code, media_type="application/json")
    if upstream.status_code >= 400:
        try:
            content = await upstream.aread()
        finally:
            await upstream.aclose()
            await client.aclose()
        return Response(content=content, status_code=upstream.status_code, media_type=upstream.headers.get("content-type", "application/json"))

    async def relay() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        relay(),
        status_code=upstream.status_code,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/mcp/tools", response_model=list[MCPToolOut])
async def list_mcp_tools(
    _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    _, tools = await ensure_mcp_settings(session)
    return [
        {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "enabled": tool.enabled,
            "scope": MCP_TOOL_SCOPE.get(tool.name, "public"),
            "endpoint": "/mcp/admin" if MCP_TOOL_SCOPE.get(tool.name) == "admin" else "/mcp",
        }
        for tool in tools
    ]


@router.patch(
    "/mcp/tools/{tool_id}", response_model=MCPToolOut, dependencies=[Depends(verify_csrf)]
)
async def update_mcp_tool(
    tool_id: int,
    payload: MCPToolUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> MCPToolSetting:
    tool = await session.get(MCPToolSetting, tool_id)
    if not tool:
        raise HTTPException(404, "MCP 工具不存在")
    tool.enabled = payload.enabled
    await write_audit(
        session, admin, "mcp.tool.update", "mcp_tool", str(tool.id), payload.model_dump()
    )
    await session.commit()
    await session.refresh(tool)
    return tool


@router.patch("/users/{user_id}/role", response_model=UserOut, dependencies=[Depends(verify_csrf)])
async def update_role(
    user_id: int,
    payload: RoleUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id and payload.role != Role.admin:
        raise HTTPException(status_code=409, detail="不能移除自己的管理员权限")
    user.role = payload.role
    await write_audit(
        session, admin, "user.role.update", "user", str(user.id), payload.model_dump(mode="json")
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/audit-logs")
async def list_audit_logs(
    _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = list(
        await session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    )
    actor_ids = {item.actor_id for item in rows if item.actor_id}
    actors = (
        {}
        if not actor_ids
        else {
            user.id: user
            for user in await session.scalars(select(User).where(User.id.in_(actor_ids)))
        }
    )
    ids_by_type: dict[str, set[int]] = {}
    for item in rows:
        try:
            ids_by_type.setdefault(item.target_type, set()).add(int(item.target_id))
        except ValueError:
            continue
    target_names: dict[tuple[str, int], str] = {}
    lookups = {
        "user": (User, User.display_name),
        "wiki": (WikiArticle, WikiArticle.title),
        "wiki_category": (Category, Category.name),
        "skill": (SkillPackage, SkillPackage.name),
        "course": (Course, Course.title),
        "lesson": (Lesson, Lesson.title),
        "projects": (ProjectSubmission, ProjectSubmission.name),
        "project": (ProjectSubmission, ProjectSubmission.name),
    }
    for target_type, (model, field) in lookups.items():
        ids = ids_by_type.get(target_type, set())
        if ids:
            records = list(await session.scalars(select(model).where(model.id.in_(ids))))
            for record in records:
                target_names[(target_type, record.id)] = getattr(record, field.key)
    return [
        {
            "id": item.id,
            "actor_id": item.actor_id,
            "actor_name": actors.get(item.actor_id).display_name
            if item.actor_id in actors
            else "系统",
            "actor_email": actors.get(item.actor_id).email if item.actor_id in actors else "",
            "action": item.action,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "target_name": (
                json.loads(item.detail or "{}").get("title")
                or json.loads(item.detail or "{}").get("name")
                or target_names.get((item.target_type, int(item.target_id)), "")
            )
            if item.target_id.isdigit()
            else "",
            "detail": json.loads(item.detail or "{}"),
            "created_at": item.created_at,
        }
        for item in rows
    ]


async def resolve_category_and_tags(
    session: AsyncSession, category_name: str, tag_names: list[str], category_id: int | None = None
) -> tuple[Category, list[Tag]]:
    category = await session.get(Category, category_id) if category_id else None
    if category_id and not category:
        raise HTTPException(404, "分类不存在")
    category_slug = category_name.strip().lower().replace(" ", "-")
    if not category:
        category = await session.scalar(select(Category).where(Category.slug == category_slug))
    if not category:
        category = Category(slug=category_slug, name=category_name.strip())
        session.add(category)
        await session.flush()
    tags: list[Tag] = []
    for name in tag_names:
        slug = name.strip().lower().replace(" ", "-")
        tag = await session.scalar(select(Tag).where(Tag.slug == slug))
        if not tag:
            tag = Tag(slug=slug, name=name.strip())
            session.add(tag)
            await session.flush()
        tags.append(tag)
    return category, tags


@router.post(
    "/wiki",
    response_model=WikiDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_wiki(
    payload: WikiWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> WikiArticle:
    if await session.scalar(select(WikiArticle).where(WikiArticle.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="词条标识已存在")
    category, tags = await resolve_category_and_tags(
        session, payload.category, payload.tags, payload.category_id
    )
    article = WikiArticle(
        slug=payload.slug,
        title=payload.title,
        summary=payload.summary,
        body_markdown=payload.body_markdown,
        content_json=normalize_content_json(payload.content_json, payload.body_markdown),
        difficulty=payload.difficulty,
        status=payload.status,
        category=category,
        tags=tags,
        order_index=payload.order_index,
    )
    session.add(article)
    await session.flush()
    await write_audit(
        session,
        admin,
        "wiki.create",
        "wiki",
        str(article.id),
        {
            "slug": article.slug,
            "title": article.title,
            "category_id": article.category_id,
            "status": str(article.status),
        },
    )
    await session.commit()
    return await session.scalar(
        select(WikiArticle)
        .where(WikiArticle.id == article.id)
        .options(selectinload(WikiArticle.category), selectinload(WikiArticle.tags))
    )


@router.put("/wiki/{article_id}", response_model=WikiDetail, dependencies=[Depends(verify_csrf)])
async def update_wiki(
    article_id: int,
    payload: WikiWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> WikiArticle:
    article = await session.scalar(
        select(WikiArticle)
        .where(WikiArticle.id == article_id)
        .options(selectinload(WikiArticle.category), selectinload(WikiArticle.tags))
    )
    if not article:
        raise HTTPException(status_code=404, detail="词条不存在")
    if await session.scalar(
        select(WikiArticle.id).where(WikiArticle.slug == payload.slug, WikiArticle.id != article_id)
    ):
        raise HTTPException(409, "词条标识已存在")
    category, tags = await resolve_category_and_tags(
        session, payload.category, payload.tags, payload.category_id
    )
    article.slug = payload.slug
    article.title = payload.title
    article.summary = payload.summary
    article.body_markdown = payload.body_markdown
    article.content_json = normalize_content_json(payload.content_json, payload.body_markdown)
    article.difficulty = payload.difficulty
    article.status = payload.status
    article.category = category
    article.tags = tags
    article.order_index = payload.order_index
    article.version += 1
    await write_audit(
        session,
        admin,
        "wiki.update",
        "wiki",
        str(article.id),
        {
            "slug": article.slug,
            "title": article.title,
            "category_id": article.category_id,
            "status": str(article.status),
            "version": article.version,
        },
    )
    await session.commit()
    return article


@router.post(
    "/skills/upload",
    response_model=SkillOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def upload_skill(
    archive: UploadFile = File(...),
    version: str = Form(..., pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$"),
    publish: bool = Form(False),
    summary: str = Form("", max_length=2000),
    content_category_id: int | None = Form(None),
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
) -> SkillPackage:
    data = await archive.read(5 * 1024 * 1024 + 1)
    try:
        checked = validate_skill_archive(data)
    except SkillValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    slug = checked["name"]
    if await session.scalar(
        select(SkillPackage).where(SkillPackage.slug == slug, SkillPackage.version == version)
    ):
        raise HTTPException(status_code=409, detail="该版本已存在")
    category = (
        await session.get(ContentCategory, content_category_id)
        if content_category_id
        else await session.scalar(
            select(ContentCategory)
            .where(ContentCategory.kind == "skill")
            .order_by(ContentCategory.order_index, ContentCategory.id)
        )
    )
    if content_category_id and (not category or category.kind != "skill"):
        raise HTTPException(422, "请选择有效的内容分区")
    skill = SkillPackage(
        owner_id=admin.id,
        content_category_id=category.id if category else None,
        content_category=category,
        slug=slug,
        name=checked["name"],
        summary=summary.strip() or checked["description"],
        version=version,
        license_name=checked["license"],
        compatibility=checked["compatibility"],
        skill_md=checked["skill_md"],
        files_json=checked["files_json"],
        sha256=checked["sha256"],
        status=PublicationStatus.published if publish else PublicationStatus.draft,
    )
    session.add(skill)
    await session.flush()
    await write_audit(session, admin, "skill.upload", "skill", str(skill.id), {"version": version})
    await session.commit()
    return await session.scalar(
        select(SkillPackage)
        .options(selectinload(SkillPackage.content_category))
        .where(SkillPackage.id == skill.id)
    )


@router.get("/status", response_model=Message)
async def admin_status(_admin: User = Depends(admin_only)) -> Message:
    return Message(message="后台服务正常")


@router.get("/courses", response_model=list[AdminCourseOut])
async def list_admin_courses(
    _admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    return list(
        await session.scalars(
            select(Course)
            .options(selectinload(Course.lessons))
            .order_by(Course.order_index, Course.id)
        )
    )


async def save_course(payload: CourseWrite, course: Course, session: AsyncSession, admin: User):
    from sqlalchemy.exc import IntegrityError

    if course.id and not payload.slug:
        payload.slug = course.slug
    if course.id and course.is_standalone != payload.is_standalone:
        raise HTTPException(422, "不能直接改变目录类型")
    if payload.is_standalone:
        if len(payload.lessons) != 1:
            raise HTTPException(422, "无分类条目必须且只能包含一篇正文")
        payload.title = payload.lessons[0].title
        payload.slug = payload.lessons[0].slug
        payload.status = payload.lessons[0].status
    existing = {lesson.id: lesson for lesson in course.lessons}
    ids = [lesson.id for lesson in payload.lessons if lesson.id is not None]
    if len(ids) != len(set(ids)) or set(ids) != set(existing):
        raise HTTPException(422, "课文目录已变化，请重新加载；移除条目请使用专用移除入口")
    slugs = [lesson.slug for lesson in payload.lessons]
    if len(slugs) != len(set(slugs)):
        raise HTTPException(422, "课文标识不能重复")
    for key, value in payload.model_dump(exclude={"lessons"}).items():
        setattr(course, key, value)
    for item in payload.lessons:
        item.body_markdown = with_legacy_cards(
            item.body_markdown, item.objective, item.practice, item.completion_criteria
        )
        item.content_json = normalize_content_json(item.content_json, item.body_markdown)
        item.objective = item.practice = item.completion_criteria = ""
        lesson = existing.get(item.id) if item.id else None
        if lesson is None:
            lesson = Lesson()
            course.lessons.append(lesson)
        for key, value in item.model_dump(exclude={"id"}).items():
            setattr(lesson, key, value)
    session.add(course)
    try:
        await session.flush()
        await write_audit(session, admin, "course.save", "course", str(course.id))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "课程或课文标识已存在，请使用其他标识") from None
    return await session.scalar(
        select(Course)
        .where(Course.id == course.id)
        .options(selectinload(Course.lessons))
        .execution_options(populate_existing=True)
    )


@router.post("/courses", response_model=AdminCourseOut, dependencies=[Depends(verify_csrf)])
async def create_course(
    payload: CourseWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    if not payload.slug:
        payload.slug = f"course-{uuid.uuid4().hex[:12]}"
    return await save_course(payload, Course(lessons=[]), session, admin)


@router.put(
    "/courses/{course_id}", response_model=AdminCourseOut, dependencies=[Depends(verify_csrf)]
)
async def update_course(
    course_id: int,
    payload: CourseWrite,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    course = await session.scalar(
        select(Course).where(Course.id == course_id).options(selectinload(Course.lessons))
    )
    if not course:
        raise HTTPException(404, "课程不存在")
    return await save_course(payload, course, session, admin)


@router.patch(
    "/lessons/{lesson_id}/status", response_model=Message, dependencies=[Depends(verify_csrf)]
)
async def update_lesson_status(
    lesson_id: int,
    payload: ContentStatusUpdate,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    lesson = await session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "条目不存在")
    lesson.status = payload.status
    course = await session.get(Course, lesson.course_id)
    if course.is_standalone:
        course.status = payload.status
    await write_audit(
        session, admin, "lesson.status.update", "lesson", str(lesson.id), payload.model_dump()
    )
    await session.commit()
    return Message(message="条目状态已更新")


@router.delete("/{resource}/{item_id}", response_model=Message, dependencies=[Depends(verify_csrf)])
async def remove_resource(
    resource: Literal["courses", "lessons", "wiki", "projects", "skills", "users"],
    item_id: int,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    model = {
        "courses": Course,
        "lessons": Lesson,
        "wiki": WikiArticle,
        "projects": ProjectSubmission,
        "skills": SkillPackage,
        "users": User,
    }[resource]
    item = await session.get(model, item_id)
    if not item:
        raise HTTPException(404, "该记录不存在或已移除")
    if resource == "users":
        if item_id == admin.id:
            raise HTTPException(409, "不能移除当前登录账号")
        if await session.scalar(
            select(ReviewEvent.id).where(ReviewEvent.reviewer_id == item_id).limit(1)
        ):
            raise HTTPException(409, "该账号有审核历史，请使用停用以保留审核记录")
        await session.execute(
            update(AuditLog).where(AuditLog.actor_id == item_id).values(actor_id=None)
        )
    name = (
        getattr(item, "title", None)
        or getattr(item, "name", None)
        or getattr(item, "display_name", "")
    )
    await write_audit(session, admin, f"{resource}.delete", resource, str(item_id), {"name": name})
    if resource == "lessons":
        parent = await session.get(Course, item.course_id)
        if parent and parent.is_standalone:
            await session.execute(delete(Course).where(Course.id == parent.id))
        else:
            await session.execute(delete(model).where(model.id == item_id))
    else:
        await session.execute(delete(model).where(model.id == item_id))
    await session.commit()
    return Message(message="已移除")


@router.post(
    "/{resource}/{item_id}/move", response_model=Message, dependencies=[Depends(verify_csrf)]
)
async def move_directory_item(
    resource: Literal["courses", "lessons"],
    item_id: int,
    payload: DirectoryMove,
    admin: User = Depends(admin_only),
    session: AsyncSession = Depends(get_session),
):
    model = Course if resource == "courses" else Lesson
    item = await session.get(model, item_id)
    if not item:
        raise HTTPException(404, "目录项不存在")
    condition = (
        Course.difficulty == item.difficulty
        if resource == "courses"
        else Lesson.course_id == item.course_id
    )
    siblings = list(
        await session.scalars(select(model).where(condition).order_by(model.order_index, model.id))
    )
    index = next(i for i, sibling in enumerate(siblings) if sibling.id == item_id)
    target = index + payload.offset
    if target < 0 or target >= len(siblings):
        raise HTTPException(409, "已在当前列表边界")
    siblings[index], siblings[target] = siblings[target], siblings[index]
    for rank, sibling in enumerate(siblings):
        sibling.order_index = rank
    await write_audit(
        session, admin, f"{resource}.move", resource, str(item_id), {"offset": payload.offset}
    )
    await session.commit()
    return Message(message="顺序已保存")

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import require_roles, verify_csrf
from app.models import (
    AuditLog,
    Category,
    PublicationStatus,
    Role,
    SkillPackage,
    Tag,
    User,
    WikiArticle,
)
from app.schemas import Message, RoleUpdate, SkillOut, UserOut, WikiDetail, WikiWrite
from app.services.skills import SkillValidationError, validate_skill_archive

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
    rows = await session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))
    return [
        {
            "id": item.id,
            "actor_id": item.actor_id,
            "action": item.action,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "detail": json.loads(item.detail or "{}"),
            "created_at": item.created_at,
        }
        for item in rows
    ]


async def resolve_category_and_tags(
    session: AsyncSession, category_name: str, tag_names: list[str]
) -> tuple[Category, list[Tag]]:
    category_slug = category_name.strip().lower().replace(" ", "-")
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
    category, tags = await resolve_category_and_tags(session, payload.category, payload.tags)
    article = WikiArticle(
        slug=payload.slug,
        title=payload.title,
        summary=payload.summary,
        body_markdown=payload.body_markdown,
        difficulty=payload.difficulty,
        status=payload.status,
        category=category,
        tags=tags,
    )
    session.add(article)
    await session.flush()
    await write_audit(session, admin, "wiki.create", "wiki", str(article.id))
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
    category, tags = await resolve_category_and_tags(session, payload.category, payload.tags)
    article.slug = payload.slug
    article.title = payload.title
    article.summary = payload.summary
    article.body_markdown = payload.body_markdown
    article.difficulty = payload.difficulty
    article.status = payload.status
    article.category = category
    article.tags = tags
    article.version += 1
    await write_audit(session, admin, "wiki.update", "wiki", str(article.id))
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
    version: str = Form(...),
    publish: bool = Form(False),
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
    skill = SkillPackage(
        slug=slug,
        name=checked["name"],
        summary=checked["description"],
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
    await session.refresh(skill)
    return skill


@router.get("/status", response_model=Message)
async def admin_status(_admin: User = Depends(admin_only)) -> Message:
    return Message(message="后台服务正常")

import re

import yaml
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import require_user, verify_csrf
from app.models import AuditLog, ContentCategory, PublicationStatus, Role, SkillPackage, User
from app.schemas import (
    AdminSkillOut,
    SkillContentUpdate,
    SkillCreate,
    SkillIntroUpdate,
    SkillOut,
    SkillStatusUpdate,
)
from app.services.skills import (
    MAX_ARCHIVE_BYTES,
    SkillValidationError,
    build_skill_archive,
    validate_skill_archive,
)

router = APIRouter(prefix="/skills", tags=["skills"])


def audit_skill(session: AsyncSession, user: User, skill: SkillPackage, action: str) -> None:
    session.add(AuditLog(actor_id=user.id, action=action, target_type="skill", target_id=str(skill.id)))


async def save_skill(checked: dict, version: str, summary: str, publish: bool, content_category_id: int | None,
                     user: User, session: AsyncSession, tags: list[str] | None = None) -> SkillPackage:
    # A slug belongs to its original author, including when adding a new version.
    versions = list(await session.scalars(select(SkillPackage).where(SkillPackage.slug == checked["name"])))
    if user.role != Role.admin and any(item.owner_id != user.id for item in versions):
        raise HTTPException(409, "该 Skill 名称已被使用，请更换名称")
    owner_id = versions[0].owner_id if versions and versions[0].owner_id is not None else user.id
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
        owner_id=owner_id, slug=checked["name"], name=checked["name"],
        content_category_id=category.id if category else None,
        content_category=category,
        summary=summary.strip() or checked["description"], version=version,
        tags=tags or [],
        license_name=checked["license"], compatibility=checked["compatibility"],
        skill_md=checked["skill_md"], files_json=checked["files_json"], sha256=checked["sha256"],
        status=(PublicationStatus.published if user.role == Role.admin else PublicationStatus.pending_review) if publish else PublicationStatus.draft,
    )
    session.add(skill)
    try:
        await session.flush()
        audit_skill(session, user, skill, "skill.upload")
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "该版本已存在") from exc
    return await session.scalar(
        select(SkillPackage)
        .options(selectinload(SkillPackage.content_category))
        .where(SkillPackage.id == skill.id)
    )


def check_archive(data: bytes) -> dict:
    try:
        return validate_skill_archive(data)
    except SkillValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/mine", response_model=list[AdminSkillOut])
async def my_skills(user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    return list(await session.scalars(select(SkillPackage).options(selectinload(SkillPackage.content_category)).where(SkillPackage.owner_id == user.id).order_by(SkillPackage.id.desc())))


@router.post("", response_model=AdminSkillOut, status_code=201, dependencies=[Depends(verify_csrf)])
async def create_skill(payload: SkillCreate, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    metadata = yaml.safe_dump({"name": payload.name, "description": payload.description}, allow_unicode=True, sort_keys=False)
    skill_md = f"---\n{metadata}---\n\n{payload.instructions}\n"
    checked = check_archive(build_skill_archive(skill_md, "{}"))
    return await save_skill(checked, payload.version, payload.summary, payload.publish, payload.content_category_id, user, session, payload.tags)


@router.post("/upload", response_model=AdminSkillOut, status_code=201, dependencies=[Depends(verify_csrf)])
async def upload_skill(
    archive: UploadFile = File(...),
    version: str = Form("1.0.0", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$"),
    summary: str = Form("", max_length=2000), publish: bool = Form(False), content_category_id: int | None = Form(None),
    tags: list[str] = Form(default=[]),
    user: User = Depends(require_user), session: AsyncSession = Depends(get_session),
):
    data = await archive.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise HTTPException(422, "文件不能超过 5 MB")
    if (archive.filename or "").lower().endswith(".md"):
        try:
            data = build_skill_archive(data.decode("utf-8-sig"), "{}")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, "SKILL.md 必须使用 UTF-8 编码") from exc
    if len(tags) > 12:
        raise HTTPException(422, "最多添加 12 个标签")
    try:
        cleaned_tags = SkillIntroUpdate.clean_skill_tags(tags)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return await save_skill(check_archive(data), version, summary, publish, content_category_id, user, session, cleaned_tags)


async def owned_skill(skill_id: int, user: User, session: AsyncSession) -> SkillPackage:
    skill = await session.scalar(select(SkillPackage).options(selectinload(SkillPackage.content_category)).where(SkillPackage.id == skill_id))
    if not skill or skill.owner_id != user.id:
        raise HTTPException(404, "Skill 不存在或不属于你")
    return skill


@router.get("/{skill_id}/content", response_class=PlainTextResponse)
async def owned_skill_content(skill_id: int, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    return PlainTextResponse((await owned_skill(skill_id, user, session)).skill_md)


@router.patch("/{skill_id}/content", response_model=AdminSkillOut, dependencies=[Depends(verify_csrf)])
async def update_skill_content(
    skill_id: int, payload: SkillContentUpdate,
    user: User = Depends(require_user), session: AsyncSession = Depends(get_session),
):
    skill = await owned_skill(skill_id, user, session)
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
    if user.role != Role.admin and skill.status in {PublicationStatus.published, PublicationStatus.pending_review}:
        skill.status = PublicationStatus.pending_review
        skill.review_note = None
    audit_skill(session, user, skill, "skill.content.update")
    await session.commit()
    await session.refresh(skill, ["content_category"])
    return skill


@router.patch("/{skill_id}/intro", response_model=AdminSkillOut, dependencies=[Depends(verify_csrf)])
async def update_intro(skill_id: int, payload: SkillIntroUpdate, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    skill = await owned_skill(skill_id, user, session)
    category = None
    if payload.content_category_id is not None:
        category = await session.get(ContentCategory, payload.content_category_id)
        if not category or category.kind != "skill":
            raise HTTPException(422, "请选择有效的技能分类")
    changed = skill.summary != payload.summary or (payload.tags is not None and skill.tags != payload.tags) or (category is not None and skill.content_category_id != category.id)
    if changed and user.role != Role.admin and skill.status in {PublicationStatus.published, PublicationStatus.pending_review}:
        skill.status = PublicationStatus.pending_review
        skill.review_note = None
    skill.summary = payload.summary
    if payload.tags is not None:
        skill.tags = payload.tags
    if category is not None:
        skill.content_category_id = category.id
    audit_skill(session, user, skill, "skill.intro.update")
    await session.commit()
    await session.refresh(skill, ["content_category"])
    return skill


@router.patch("/{skill_id}/status", response_model=AdminSkillOut, dependencies=[Depends(verify_csrf)])
async def update_status(skill_id: int, payload: SkillStatusUpdate, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    skill = await owned_skill(skill_id, user, session)
    skill.status = (PublicationStatus.published if user.role == Role.admin else PublicationStatus.pending_review) if payload.status in {"published", "pending_review"} else PublicationStatus.draft
    skill.review_note = None
    audit_skill(session, user, skill, "skill.status.update")
    await session.commit()
    await session.refresh(skill, ["content_category"])
    return skill


@router.delete("/{skill_id}", dependencies=[Depends(verify_csrf)])
async def delete_skill(skill_id: int, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    skill = await owned_skill(skill_id, user, session)
    await session.delete(skill)
    audit_skill(session, user, skill, "skill.delete")
    await session.commit()
    return {"message": "Skill 已删除"}


@router.get("", response_model=list[SkillOut])
async def list_skills(session: AsyncSession = Depends(get_session)) -> list[SkillPackage]:
    return list(
        await session.scalars(
            select(SkillPackage).options(selectinload(SkillPackage.content_category))
            .where(SkillPackage.status == PublicationStatus.published)
            .order_by(SkillPackage.name, SkillPackage.version.desc())
        )
    )


@router.get("/{slug}", response_model=SkillOut)
async def get_skill(slug: str, session: AsyncSession = Depends(get_session)) -> SkillPackage:
    skill = await session.scalar(
        select(SkillPackage).options(selectinload(SkillPackage.content_category))
        .where(SkillPackage.slug == slug, SkillPackage.status == PublicationStatus.published)
        .order_by(SkillPackage.version.desc())
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return skill

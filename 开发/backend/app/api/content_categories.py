from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_roles, verify_csrf
from app.models import ContentCategory, ProjectSubmission, Role, SkillPackage, User
from app.schemas import ContentCategoryOut, ContentCategoryWrite, Message

router = APIRouter(prefix="/content-categories", tags=["content-categories"])
admin_only = require_roles(Role.admin)

@router.get("", response_model=list[ContentCategoryOut])
async def list_content_categories(kind: str | None = None, session: AsyncSession = Depends(get_session)):
    statement = select(ContentCategory).order_by(ContentCategory.kind, ContentCategory.order_index, ContentCategory.name)
    if kind in {"project", "skill"}:
        statement = statement.where(ContentCategory.kind == kind)
    return list(await session.scalars(statement))

@router.post("", response_model=ContentCategoryOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
async def create_content_category(payload: ContentCategoryWrite, _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    slug = payload.slug or f"{payload.kind}-category"
    duplicate = await session.scalar(select(ContentCategory).where((ContentCategory.kind == payload.kind) & ((ContentCategory.slug == slug) | (ContentCategory.name == payload.name))))
    if duplicate:
        raise HTTPException(409, "该类型下的分区标识或名称已存在")
    category = ContentCategory(kind=payload.kind, name=payload.name.strip(), slug=slug, order_index=payload.order_index)
    session.add(category)
    await session.flush()
    if not payload.slug:
        category.slug = f"{payload.kind}-{category.id}"
    await session.commit()
    await session.refresh(category)
    return category

@router.delete("/{category_id}", response_model=Message, dependencies=[Depends(verify_csrf)])
async def delete_content_category(category_id: int, _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    category = await session.get(ContentCategory, category_id)
    if not category:
        raise HTTPException(404, "分区不存在")
    resource = ProjectSubmission if category.kind == "project" else SkillPackage
    if await session.scalar(select(resource.id).where(resource.content_category_id == category_id).limit(1)):
        raise HTTPException(409, "该分区已有内容使用，请先调整相关内容的分区")
    await session.delete(category)
    await session.commit()
    return Message(message="分区已删除")

@router.put("/{category_id}", response_model=ContentCategoryOut, dependencies=[Depends(verify_csrf)])
async def update_content_category(category_id: int, payload: ContentCategoryWrite, _admin: User = Depends(admin_only), session: AsyncSession = Depends(get_session)):
    category = await session.get(ContentCategory, category_id)
    if not category:
        raise HTTPException(404, "分区不存在")
    if category.kind != payload.kind:
        raise HTTPException(422, "分区类型不能更改")
    slug = payload.slug or category.slug
    duplicate = await session.scalar(select(ContentCategory).where(ContentCategory.id != category_id, ContentCategory.kind == payload.kind, ((ContentCategory.slug == slug) | (ContentCategory.name == payload.name))))
    if duplicate:
        raise HTTPException(409, "该类型下的分区标识或名称已存在")
    category.kind, category.slug, category.name, category.order_index = payload.kind, slug, payload.name.strip(), payload.order_index
    await session.commit()
    await session.refresh(category)
    return category

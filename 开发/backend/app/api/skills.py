from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import PublicationStatus, SkillPackage
from app.schemas import SkillOut

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
async def list_skills(session: AsyncSession = Depends(get_session)) -> list[SkillPackage]:
    return list(
        await session.scalars(
            select(SkillPackage)
            .where(SkillPackage.status == PublicationStatus.published)
            .order_by(SkillPackage.name, SkillPackage.version.desc())
        )
    )


@router.get("/{slug}", response_model=SkillOut)
async def get_skill(slug: str, session: AsyncSession = Depends(get_session)) -> SkillPackage:
    skill = await session.scalar(
        select(SkillPackage)
        .where(SkillPackage.slug == slug, SkillPackage.status == PublicationStatus.published)
        .order_by(SkillPackage.version.desc())
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return skill

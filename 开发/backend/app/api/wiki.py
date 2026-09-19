from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Category, Difficulty, PublicationStatus, WikiArticle
from app.schemas import CategoryOut, Page, WikiDetail, WikiSummary
from app.services.search import search_wiki_articles

router = APIRouter(prefix="/wiki", tags=["wiki"])


@router.get("", response_model=Page)
async def search_wiki(
    q: str = Query(default="", max_length=300),
    phrase: str = Query(default="", max_length=80),
    category: str | None = None,
    tags: list[str] = Query(default=[]),
    difficulty: Difficulty | None = None,
    updated_after: datetime | None = None,
    sort: str = Query(default="relevance", pattern=r"^(relevance|updated_desc|title_asc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> Page:
    items, total = await search_wiki_articles(
        session,
        q=q,
        phrase=phrase,
        category=category,
        tags=tags,
        difficulty=difficulty,
        updated_after=updated_after,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return Page(
        items=[WikiSummary.model_validate(item).model_dump() for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[Category]:
    return list(
        await session.scalars(
            select(Category)
            .where(Category.articles.any(WikiArticle.status == PublicationStatus.published))
            .order_by(Category.name)
        )
    )


@router.get("/{slug}", response_model=WikiDetail)
async def get_article(slug: str, session: AsyncSession = Depends(get_session)) -> WikiArticle:
    article = await session.scalar(
        select(WikiArticle)
        .where(WikiArticle.slug == slug, WikiArticle.status == PublicationStatus.published)
        .options(selectinload(WikiArticle.category), selectinload(WikiArticle.tags))
    )
    if not article:
        raise HTTPException(status_code=404, detail="词条不存在")
    return article

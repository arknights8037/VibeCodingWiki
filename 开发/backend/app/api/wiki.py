from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Category, Difficulty, PublicationStatus, WikiArticle
from app.schemas import CategoryOut, Page, WikiDetail, WikiSummary
from app.services.search import search_wiki_articles

router = APIRouter(prefix="/wiki", tags=["wiki"])


class WikiTerm(BaseModel):
    slug: str
    title: str
    summary: str


@router.get("/terms", response_model=list[WikiTerm])
async def list_terms(
    response: Response, session: AsyncSession = Depends(get_session)
) -> list[WikiTerm]:
    """Live, lightweight index for automatic course annotations; no pagination."""
    response.headers["Cache-Control"] = "no-store"
    rows = await session.execute(
        select(WikiArticle.slug, WikiArticle.title, WikiArticle.summary)
        .where(WikiArticle.status == PublicationStatus.published)
        .order_by(WikiArticle.id)
    )
    return [WikiTerm(slug=row.slug, title=row.title, summary=row.summary) for row in rows]


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
    categories = list(await session.scalars(select(Category).order_by(Category.order_index, Category.id)))
    visible = set(await session.scalars(
        select(WikiArticle.category_id).where(WikiArticle.status == PublicationStatus.published).distinct()
    ))
    by_id = {category.id: category for category in categories}
    for category_id in list(visible):
        parent_id = by_id[category_id].parent_id
        while parent_id is not None and parent_id not in visible:
            visible.add(parent_id)
            parent_id = by_id[parent_id].parent_id
    return [category for category in categories if category.id in visible]


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

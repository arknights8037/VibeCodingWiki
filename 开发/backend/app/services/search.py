import re
from datetime import datetime

from sqlalchemy import Select, case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Difficulty, PublicationStatus, Tag, WikiArticle, article_tags

TOKEN_RE = re.compile(r'"([^"]{1,80})"|([\w\u4e00-\u9fff-]{1,80})')


def safe_fts_query(value: str) -> str:
    tokens: list[str] = []
    for phrase, word in TOKEN_RE.findall(value[:300]):
        token = (phrase or word).replace('"', '""').strip()
        if token:
            tokens.append(f'"{token}"')
    return " AND ".join(tokens[:12])


async def search_wiki_articles(
    session: AsyncSession,
    *,
    q: str = "",
    phrase: str = "",
    category: str | None = None,
    tags: list[str] | None = None,
    difficulty: Difficulty | None = None,
    updated_after: datetime | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WikiArticle], int]:
    filters = [WikiArticle.status == PublicationStatus.published]
    statement: Select = select(WikiArticle).options(
        selectinload(WikiArticle.category), selectinload(WikiArticle.tags)
    )
    if category:
        category_ids = select(Category.id).where(Category.slug == category).cte("category_descendants", recursive=True)
        category_ids = category_ids.union(
            select(Category.id).join(category_ids, Category.parent_id == category_ids.c.id)
        )
        filters.append(WikiArticle.category_id.in_(select(category_ids.c.id)))
    if difficulty:
        filters.append(WikiArticle.difficulty == difficulty)
    if updated_after:
        filters.append(WikiArticle.updated_at >= updated_after)
    if tags:
        unique_tags = sorted(set(tags[:12]))
        articles_with_all_tags = (
            select(article_tags.c.article_id)
            .join(Tag, Tag.id == article_tags.c.tag_id)
            .where(Tag.slug.in_(unique_tags))
            .group_by(article_tags.c.article_id)
            .having(func.count(func.distinct(Tag.slug)) == len(unique_tags))
        )
        filters.append(WikiArticle.id.in_(articles_with_all_tags))

    ids: list[int] | None = None
    # Keep phrase and keyword filters independent: a failed keyword match must
    # not accidentally fall back to matching only the phrase.
    phrase = phrase.strip()
    if phrase:
        filters.append(or_(
            WikiArticle.title.contains(phrase, autoescape=True),
            WikiArticle.summary.contains(phrase, autoescape=True),
            WikiArticle.body_markdown.contains(phrase, autoescape=True),
        ))
    fts_query = safe_fts_query(q)
    if fts_query:
        rows = await session.execute(
            text("SELECT rowid FROM wiki_fts WHERE wiki_fts MATCH :q ORDER BY bm25(wiki_fts)"),
            {"q": fts_query},
        )
        ids = [int(row[0]) for row in rows]
        if ids:
            filters.append(WikiArticle.id.in_(ids))
        else:
            literal = q.strip()[:100]
            filters.append(
                or_(
                    WikiArticle.title.contains(literal, autoescape=True),
                    WikiArticle.summary.contains(literal, autoescape=True),
                    WikiArticle.body_markdown.contains(literal, autoescape=True),
                )
            )
    elif q.strip():
        filters.append(or_(
            WikiArticle.title.contains(q.strip(), autoescape=True),
            WikiArticle.summary.contains(q.strip(), autoescape=True),
            WikiArticle.body_markdown.contains(q.strip(), autoescape=True),
        ))

    statement = statement.where(*filters).distinct()
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(await session.scalar(count_statement) or 0)

    if sort == "order_asc":
        statement = statement.order_by(WikiArticle.order_index.asc(), WikiArticle.id.asc())
    elif sort == "updated_desc":
        statement = statement.order_by(WikiArticle.updated_at.desc(), WikiArticle.id)
    elif sort == "title_asc":
        statement = statement.order_by(WikiArticle.title.asc(), WikiArticle.id)
    elif ids:
        ordering = {item_id: index for index, item_id in enumerate(ids)}
        statement = statement.order_by(case(ordering, value=WikiArticle.id), WikiArticle.id)
    else:
        statement = statement.order_by(WikiArticle.updated_at.desc(), WikiArticle.id)

    result = list(
        (await session.scalars(statement.offset((page - 1) * page_size).limit(page_size))).unique()
    )
    return result, total

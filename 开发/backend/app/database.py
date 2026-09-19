from collections.abc import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base
from app.services.lesson_content import with_legacy_cards

settings.data_dir.mkdir(parents=True, exist_ok=True)
engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async def init_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        columns = await connection.execute(text("PRAGMA table_info(courses)"))
        column_names = {row[1] for row in columns}
        if "is_standalone" not in column_names:
            await connection.execute(text("ALTER TABLE courses ADD COLUMN is_standalone BOOLEAN NOT NULL DEFAULT 0"))
        if "directory_collapsible" not in column_names:
            await connection.execute(text("ALTER TABLE courses ADD COLUMN directory_collapsible BOOLEAN NOT NULL DEFAULT 1"))
        user_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info(users)")))}
        if "github_username" not in user_columns:
            await connection.execute(text("ALTER TABLE users ADD COLUMN github_username VARCHAR(120)"))
        if "gitee_username" not in user_columns:
            await connection.execute(text("ALTER TABLE users ADD COLUMN gitee_username VARCHAR(120)"))
        for name, sql_type in (("real_name", "VARCHAR(80)"), ("avatar_url", "VARCHAR(500)"), ("mcp_token_hash", "VARCHAR(128)")):
            if name not in user_columns:
                await connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))
        oauth_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info(mcp_settings)")))}
        for name, sql_type in (("github_client_id", "VARCHAR(200)"), ("github_client_secret", "VARCHAR(300)"), ("gitee_client_id", "VARCHAR(200)"), ("gitee_client_secret", "VARCHAR(300)")):
            if name not in oauth_columns:
                await connection.execute(text(f"ALTER TABLE mcp_settings ADD COLUMN {name} {sql_type}"))
        category_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info(categories)")))}
        if "parent_id" not in category_columns:
            await connection.execute(text("ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL"))
        if "order_index" not in category_columns:
            await connection.execute(text("ALTER TABLE categories ADD COLUMN order_index INTEGER NOT NULL DEFAULT 0"))
        article_columns = {row[1] for row in (await connection.execute(text("PRAGMA table_info(wiki_articles)")))}
        if "order_index" not in article_columns:
            await connection.execute(text("ALTER TABLE wiki_articles ADD COLUMN order_index INTEGER NOT NULL DEFAULT 0"))
        legacy_lessons = (await connection.execute(text("SELECT id, body_markdown, objective, practice, completion_criteria FROM lessons WHERE objective != '' OR practice != '' OR completion_criteria != ''"))).mappings().all()
        for lesson in legacy_lessons:
            body = with_legacy_cards(lesson["body_markdown"], lesson["objective"], lesson["practice"], lesson["completion_criteria"])
            await connection.execute(text("UPDATE lessons SET body_markdown=:body, objective='', practice='', completion_criteria='' WHERE id=:id"), {"body": body, "id": lesson["id"]})
        statements = [
            "CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(title, summary, body_markdown, content='wiki_articles', content_rowid='id', tokenize='unicode61')",
            "CREATE TRIGGER IF NOT EXISTS wiki_fts_ai AFTER INSERT ON wiki_articles BEGIN INSERT INTO wiki_fts(rowid,title,summary,body_markdown) VALUES(new.id,new.title,new.summary,new.body_markdown); END",
            "CREATE TRIGGER IF NOT EXISTS wiki_fts_ad AFTER DELETE ON wiki_articles BEGIN INSERT INTO wiki_fts(wiki_fts,rowid,title,summary,body_markdown) VALUES('delete',old.id,old.title,old.summary,old.body_markdown); END",
            "CREATE TRIGGER IF NOT EXISTS wiki_fts_au AFTER UPDATE ON wiki_articles BEGIN INSERT INTO wiki_fts(wiki_fts,rowid,title,summary,body_markdown) VALUES('delete',old.id,old.title,old.summary,old.body_markdown); INSERT INTO wiki_fts(rowid,title,summary,body_markdown) VALUES(new.id,new.title,new.summary,new.body_markdown); END",
        ]
        for statement in statements:
            await connection.execute(text(statement))
        await connection.execute(text("INSERT INTO wiki_fts(wiki_fts) VALUES('rebuild')"))


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

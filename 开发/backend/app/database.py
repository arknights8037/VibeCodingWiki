from collections.abc import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base

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

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
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


def migrate_database() -> None:
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(config, "head")


async def init_database() -> None:
    # SQLite migrations use the synchronous driver on a worker thread so
    # server startup never blocks the event loop.
    await asyncio.to_thread(migrate_database)
    async with engine.begin() as connection:
        legacy_lessons = (
            await connection.execute(
                text(
                    "SELECT id, body_markdown, objective, practice, completion_criteria "
                    "FROM lessons WHERE objective != '' OR practice != '' OR completion_criteria != ''"
                )
            )
        ).mappings().all()
        for lesson in legacy_lessons:
            body = with_legacy_cards(
                lesson["body_markdown"],
                lesson["objective"],
                lesson["practice"],
                lesson["completion_criteria"],
            )
            await connection.execute(
                text(
                    "UPDATE lessons SET body_markdown=:body, objective='', practice='', "
                    "completion_criteria='' WHERE id=:id"
                ),
                {"body": body, "id": lesson["id"]},
            )


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

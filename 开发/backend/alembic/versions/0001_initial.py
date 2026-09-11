"""Initial schema and full-text index."""

from alembic import op
from app.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    bind.exec_driver_sql(
        "CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(title, summary, body_markdown, "
        "content='wiki_articles', content_rowid='id', tokenize='unicode61')"
    )
    bind.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS wiki_fts_ai AFTER INSERT ON wiki_articles BEGIN "
        "INSERT INTO wiki_fts(rowid,title,summary,body_markdown) "
        "VALUES(new.id,new.title,new.summary,new.body_markdown); END"
    )
    bind.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS wiki_fts_ad AFTER DELETE ON wiki_articles BEGIN "
        "INSERT INTO wiki_fts(wiki_fts,rowid,title,summary,body_markdown) "
        "VALUES('delete',old.id,old.title,old.summary,old.body_markdown); END"
    )
    bind.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS wiki_fts_au AFTER UPDATE ON wiki_articles BEGIN "
        "INSERT INTO wiki_fts(wiki_fts,rowid,title,summary,body_markdown) "
        "VALUES('delete',old.id,old.title,old.summary,old.body_markdown); "
        "INSERT INTO wiki_fts(rowid,title,summary,body_markdown) "
        "VALUES(new.id,new.title,new.summary,new.body_markdown); END"
    )


def downgrade() -> None:
    bind = op.get_bind()
    for name in ("wiki_fts_au", "wiki_fts_ad", "wiki_fts_ai"):
        bind.exec_driver_sql(f"DROP TRIGGER IF EXISTS {name}")
    bind.exec_driver_sql("DROP TABLE IF EXISTS wiki_fts")
    Base.metadata.drop_all(bind=bind)

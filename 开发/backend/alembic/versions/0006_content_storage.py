"""Version the account, skill ownership and structured content schema."""

import sqlalchemy as sa

from alembic import op

revision = "0006_content_storage"
down_revision = "0005_block_content_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("""CREATE TABLE IF NOT EXISTS content_categories (
        id INTEGER NOT NULL PRIMARY KEY, kind VARCHAR(20) NOT NULL,
        slug VARCHAR(80) NOT NULL, name VARCHAR(80) NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 0,
        UNIQUE (kind, slug), UNIQUE (kind, name))""")
    # Older development installations added some fields outside Alembic.
    # Inspect first so both those databases and clean installs can upgrade.
    additions = {
        "lessons": {"content_json": "TEXT NOT NULL DEFAULT ''"},
        "wiki_articles": {"content_json": "TEXT NOT NULL DEFAULT ''"},
        "users": {
            "real_name": "VARCHAR(80)", "avatar_url": "VARCHAR(500)",
            "mcp_token_hash": "VARCHAR(128)", "github_username": "VARCHAR(120)",
            "gitee_username": "VARCHAR(120)",
        },
        "mcp_settings": {
            "github_client_id": "VARCHAR(200)", "github_client_secret": "VARCHAR(300)",
            "gitee_client_id": "VARCHAR(200)", "gitee_client_secret": "VARCHAR(300)",
        },
        "skill_packages": {
            "review_note": "TEXT",
            "owner_id": "INTEGER REFERENCES users(id) ON DELETE SET NULL",
            "category_id": "INTEGER REFERENCES categories(id) ON DELETE SET NULL",
            "content_category_id": "INTEGER REFERENCES content_categories(id) ON DELETE SET NULL",
        },
        "project_submissions": {
            "category_id": "INTEGER REFERENCES categories(id) ON DELETE SET NULL",
            "content_category_id": "INTEGER REFERENCES content_categories(id) ON DELETE SET NULL",
        },
    }
    for table, fields in additions.items():
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for name, definition in fields.items():
            if name not in columns:
                bind.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    for table, fields in {
        "content_categories": ("kind", "order_index"),
        "skill_packages": ("owner_id", "category_id", "content_category_id"),
        "project_submissions": ("category_id", "content_category_id"),
        "categories": ("parent_id", "order_index"),
        "wiki_articles": ("order_index",),
    }.items():
        for name in fields:
            bind.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS ix_{table}_{name} ON {table} ({name})")

    from app.services.lesson_content import with_legacy_cards

    lessons = bind.execute(sa.text(
        "SELECT id, body_markdown, objective, practice, completion_criteria FROM lessons "
        "WHERE objective != '' OR practice != '' OR completion_criteria != ''"
    )).mappings().all()
    for lesson in lessons:
        body = with_legacy_cards(lesson["body_markdown"], lesson["objective"], lesson["practice"], lesson["completion_criteria"])
        bind.execute(sa.text(
            "UPDATE lessons SET body_markdown=:body, objective='', practice='', completion_criteria='' WHERE id=:id"
        ), {"body": body, "id": lesson["id"]})
    bind.exec_driver_sql("INSERT INTO wiki_fts(wiki_fts) VALUES('rebuild')")


def downgrade() -> None:
    raise RuntimeError("This data migration cannot be safely reversed; restore a verified backup.")

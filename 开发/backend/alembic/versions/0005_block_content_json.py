"""Compatibility marker for databases created by the earlier block editor work."""

revision = "0005_block_content_json"
down_revision = "0004_nested_wiki_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The complete, idempotent schema/data work is in 0006_content_storage.
    pass


def downgrade() -> None:
    raise RuntimeError("This compatibility migration cannot be safely reversed.")

"""Store user-defined skill tags without changing package archives."""

import sqlalchemy as sa

from alembic import op

revision = "0007_skill_tags"
down_revision = "0006_content_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skill_packages", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("skill_packages", "tags")

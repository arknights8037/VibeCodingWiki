"""Add administrator-managed AI API settings."""

import sqlalchemy as sa

from alembic import op

revision = "0008_ai_api_settings"
down_revision = "0007_skill_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mcp_settings", sa.Column("ai_base_url", sa.String(length=500), nullable=True))
    op.add_column("mcp_settings", sa.Column("ai_model", sa.String(length=200), nullable=True))
    op.add_column("mcp_settings", sa.Column("ai_api_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_settings", "ai_api_key")
    op.drop_column("mcp_settings", "ai_model")
    op.drop_column("mcp_settings", "ai_base_url")

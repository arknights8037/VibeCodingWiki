"""Add nested, ordered wiki categories and article ordering."""
import sqlalchemy as sa

from alembic import op

revision = "0004_nested_wiki_categories"
down_revision = "0003_standalone_entries"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    category_columns = {column["name"] for column in inspector.get_columns("categories")}
    article_columns = {column["name"] for column in inspector.get_columns("wiki_articles")}
    if "parent_id" not in category_columns:
        op.add_column("categories", sa.Column("parent_id", sa.Integer(), nullable=True))
        op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
        op.create_foreign_key("fk_categories_parent_id", "categories", "categories", ["parent_id"], ["id"], ondelete="SET NULL")
    if "order_index" not in category_columns:
        op.add_column("categories", sa.Column("order_index", sa.Integer(), server_default="0", nullable=False))
        op.create_index("ix_categories_order_index", "categories", ["order_index"])
    if "order_index" not in article_columns:
        op.add_column("wiki_articles", sa.Column("order_index", sa.Integer(), server_default="0", nullable=False))
        op.create_index("ix_wiki_articles_order_index", "wiki_articles", ["order_index"])


def downgrade():
    op.drop_index("ix_wiki_articles_order_index", table_name="wiki_articles")
    op.drop_column("wiki_articles", "order_index")
    op.drop_index("ix_categories_order_index", table_name="categories")
    op.drop_column("categories", "order_index")
    op.drop_constraint("fk_categories_parent_id", "categories", type_="foreignkey")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_column("categories", "parent_id")

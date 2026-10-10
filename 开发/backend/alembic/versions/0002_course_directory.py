"""Add persisted per-category directory folding preference."""
import sqlalchemy as sa

from alembic import op

revision = '0002_course_directory'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    if 'directory_collapsible' not in {column['name'] for column in sa.inspect(op.get_bind()).get_columns('courses')}:
        op.add_column('courses', sa.Column('directory_collapsible', sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade():
    op.drop_column('courses', 'directory_collapsible')

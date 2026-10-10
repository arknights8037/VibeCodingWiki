"""Support root entries without a visible category."""
import sqlalchemy as sa

from alembic import op

revision = '0003_standalone_entries'
down_revision = '0002_course_directory'
branch_labels = None
depends_on = None

def upgrade():
    if 'is_standalone' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('courses')}:
        op.add_column('courses', sa.Column('is_standalone', sa.Boolean(), server_default=sa.false(), nullable=False))

def downgrade():
    op.drop_column('courses', 'is_standalone')

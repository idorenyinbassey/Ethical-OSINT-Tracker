"""add credentials column to apiconfig
Revision ID: e9a1add_credentials
Revises: 70e3958a81f9
Create Date: 2025-11-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e9a1add_credentials'
down_revision = '70e3958a81f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('apiconfig'):
        cols = [c['name'] for c in inspector.get_columns('apiconfig')]
        if 'credentials' not in cols:
            op.add_column('apiconfig', sa.Column('credentials', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('apiconfig'):
        cols = [c['name'] for c in inspector.get_columns('apiconfig')]
        if 'credentials' in cols:
            op.drop_column('apiconfig', 'credentials')

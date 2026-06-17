"""Add confidence and updated_at to investigation

Revision ID: b2c4e6a8d0f2
Revises: e9a1add_credentials
Create Date: 2026-06-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c4e6a8d0f2'
down_revision = 'e9a1add_credentials'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('investigation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confidence', sa.String(), nullable=True, server_default='UNVERIFIED'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('investigation', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('confidence')

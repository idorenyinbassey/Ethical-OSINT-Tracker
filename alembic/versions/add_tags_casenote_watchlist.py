"""Add tags to investigation; create casenote and watchlist tables

Revision ID: c3d5f7a9b1e3
Revises: b2c4e6a8d0f2
Create Date: 2026-06-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d5f7a9b1e3'
down_revision = ('b2c4e6a8d0f2', 'a8c3d5addcase')
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op as _op
    from sqlalchemy import inspect
    bind = _op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    inv_cols = [c['name'] for c in inspector.get_columns('investigation')]

    if 'tags' not in inv_cols:
        with op.batch_alter_table('investigation', schema=None) as batch_op:
            batch_op.add_column(sa.Column('tags', sa.String(), nullable=True, server_default=''))

    if 'casenote' not in existing_tables:
        op.create_table(
            'casenote',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('case.id'), nullable=False, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
            sa.Column('username', sa.String(), nullable=False, server_default=''),
            sa.Column('kind', sa.String(), nullable=False, server_default='observation'),
            sa.Column('body', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )

    if 'watchlist' not in existing_tables:
        op.create_table(
            'watchlist',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('query', sa.String(), nullable=False),
            sa.Column('kind', sa.String(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('case.id'), nullable=True, index=True),
            sa.Column('notes', sa.String(), nullable=False, server_default=''),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('last_checked', sa.DateTime(), nullable=True),
            sa.Column('last_result_hash', sa.String(), nullable=False, server_default=''),
        )


def downgrade():
    op.drop_table('watchlist')
    op.drop_table('casenote')
    with op.batch_alter_table('investigation', schema=None) as batch_op:
        batch_op.drop_column('tags')

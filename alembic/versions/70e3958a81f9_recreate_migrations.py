"""recreate migrations
Revision ID: 70e3958a81f9
Revises: 
Create Date: 2025-11-25 19:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '70e3958a81f9'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('user'):
        op.create_table(
            'user',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('username', sa.String(length=255), nullable=False),
            sa.Column('password_hash', sa.String(length=512), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.UniqueConstraint('username', name='uq_user_username'),
        )

    if not inspector.has_table('investigation'):
        op.create_table(
            'investigation',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('kind', sa.String(length=255), nullable=False),
            sa.Column('query', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('result_json', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        )

    if not inspector.has_table('apiconfig'):
        op.create_table(
            'apiconfig',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('service_name', sa.String(length=255), nullable=False),
            sa.Column('api_key', sa.String(length=2048), nullable=False),
            sa.Column('base_url', sa.String(length=1024), nullable=False),
            sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('rate_limit', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
        )

    if not inspector.has_table('case'):
        op.create_table(
            'case',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'open'")),
            sa.Column('priority', sa.String(length=50), nullable=False, server_default=sa.text("'medium'")),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('owner_user_id', sa.Integer(), nullable=True),
        )

    if not inspector.has_table('intelligencereport'):
        op.create_table(
            'intelligencereport',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('summary', sa.Text(), nullable=False),
            sa.Column('indicators', sa.Text(), nullable=False),
            sa.Column('related_case_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('author_user_id', sa.Integer(), nullable=True),
        )

    if not inspector.has_table('team'):
        op.create_table(
            'team',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('owner_user_id', sa.Integer(), nullable=True),
        )

    if not inspector.has_table('teammember'):
        op.create_table(
            'teammember',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False, server_default=sa.text("'member'")),
            sa.Column('joined_at', sa.DateTime(), nullable=False),
        )

    if not inspector.has_table('auditlog'):
        op.create_table(
            'auditlog',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('event', sa.String(length=255), nullable=False),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop in reverse-creation order, only if the table exists.
    if inspector.has_table('teammember'):
        op.drop_table('teammember')
    if inspector.has_table('team'):
        op.drop_table('team')
    if inspector.has_table('intelligencereport'):
        op.drop_table('intelligencereport')
    if inspector.has_table('case'):
        op.drop_table('case')
    if inspector.has_table('apiconfig'):
        op.drop_table('apiconfig')
    if inspector.has_table('investigation'):
        op.drop_table('investigation')
    if inspector.has_table('user'):
        op.drop_table('user')
    if inspector.has_table('auditlog'):
        op.drop_table('auditlog')

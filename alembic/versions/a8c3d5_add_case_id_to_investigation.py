"""add case_id to investigation
Revision ID: a8c3d5addcase
Revises: e9a1add_credentials
Create Date: 2025-11-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a8c3d5addcase'
down_revision = 'e9a1add_credentials'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Ensure the investigation table exists
    if inspector.has_table('investigation'):
        cols = [c['name'] for c in inspector.get_columns('investigation')]
        if 'case_id' not in cols:
            op.add_column('investigation', sa.Column('case_id', sa.Integer(), nullable=True))
            # Create foreign key if case table exists
            if inspector.has_table('case'):
                try:
                    op.create_foreign_key('fk_investigation_case', 'investigation', 'case', ['case_id'], ['id'])
                except Exception:
                    # if FK creation fails, ignore to keep migration idempotent
                    pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('investigation'):
        cols = [c['name'] for c in inspector.get_columns('investigation')]
        if 'case_id' in cols:
            # drop foreign key if exists
            try:
                op.drop_constraint('fk_investigation_case', 'investigation', type_='foreignkey')
            except Exception:
                pass
            try:
                op.drop_column('investigation', 'case_id')
            except Exception:
                pass

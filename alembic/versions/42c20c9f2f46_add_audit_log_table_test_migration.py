"""Add audit_log table (test migration).

Revision ID: 42c20c9f2f46
Revises: 5620a639f898
Create Date: 2025-11-24
"""
from alembic import op
import sqlalchemy as sa

revision = "42c20c9f2f46"
down_revision = "5620a639f898"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auditlog",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("auditlog")

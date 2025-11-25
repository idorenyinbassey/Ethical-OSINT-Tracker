"""Alembic migration script template."""
from alembic import op
import sqlalchemy as sa

${message}
revision = '${up_revision}'
down_revision = ${down_revision | repr}
branch_labels = ${branch_labels | repr}
depends_on = ${depends_on | repr}

def upgrade():
    pass

def downgrade():
    pass

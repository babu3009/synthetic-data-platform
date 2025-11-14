"""add_description_to_projects

Revision ID: 2025_11_14_2352
Revises: cf11522998c9
Create Date: 2025-11-14 23:52:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_11_14_2352'
down_revision = 'cf11522998c9'
branch_labels = None
depends_on = None

SCHEMA = "synthetic_data"


def upgrade() -> None:
    """Add description column to projects table."""
    op.add_column(
        'projects',
        sa.Column('description', sa.String(length=1000), nullable=True),
        schema=SCHEMA
    )


def downgrade() -> None:
    """Remove description column from projects table."""
    op.drop_column('projects', 'description', schema=SCHEMA)

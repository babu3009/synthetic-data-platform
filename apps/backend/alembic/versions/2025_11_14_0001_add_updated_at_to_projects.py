"""Add updated_at to projects

Revision ID: 2025_11_14_0001
Revises: 2025_11_09_0008
Create Date: 2025-11-14
"""
from alembic import op
import sqlalchemy as sa
from app.db.base import SCHEMA_NAME

# revision identifiers, used by Alembic.
revision = "2025_11_14_0001"
down_revision = "2025_11_09_0008"
branch_labels = None
depends_on = None

SCHEMA = SCHEMA_NAME


def upgrade() -> None:
    # Add updated_at column with default to now()
    op.execute(
        f"ALTER TABLE {SCHEMA}.projects "
        f"ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()"
    )


def downgrade() -> None:
    op.drop_column("projects", "updated_at", schema=SCHEMA)

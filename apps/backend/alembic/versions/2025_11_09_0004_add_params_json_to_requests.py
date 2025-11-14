"""Add params_json column to requests

Revision ID: 2025_11_09_0004
Revises: 2025_11_09_0003
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from app.db.base import SCHEMA_NAME


# revision identifiers, used by Alembic.
revision = "2025_11_09_0004"
down_revision = "2025_11_09_0003"
branch_labels = None
depends_on = None

SCHEMA = SCHEMA_NAME


def upgrade() -> None:
    # Add params_json JSONB column (nullable) to requests
    op.execute(text(f"ALTER TABLE {SCHEMA}.requests ADD COLUMN IF NOT EXISTS params_json JSONB"))


def downgrade() -> None:
    # Drop params_json column
    op.drop_column("requests", "params_json", schema=SCHEMA)

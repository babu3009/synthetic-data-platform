"""Add params_json column to requests

Revision ID: 2025_11_09_0004
Revises: 2025_11_09_0003
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "2025_11_09_0004"
down_revision = "2025_11_09_0003"
branch_labels = None
depends_on = None

SCHEMA = "synthetic_data"


def upgrade() -> None:
    # Add params_json JSONB column (nullable) to requests
    op.add_column(
        "requests",
        sa.Column(
            "params_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    # Drop params_json column
    op.drop_column("requests", "params_json", schema=SCHEMA)

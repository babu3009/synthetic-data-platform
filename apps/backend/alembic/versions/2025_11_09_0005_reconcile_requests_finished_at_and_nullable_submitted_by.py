"""Reconcile requests: add finished_at, relax submitted_by nullability

Revision ID: 2025_11_09_0005
Revises: 2025_11_09_0004
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from app.db.base import SCHEMA_NAME


# revision identifiers, used by Alembic.
revision = "2025_11_09_0005"
down_revision = "2025_11_09_0004"
branch_labels = None
depends_on = None

SCHEMA = SCHEMA_NAME


def upgrade() -> None:
    # Add finished_at column if not present
    op.execute(text(f"ALTER TABLE {SCHEMA}.requests ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ"))

    # Make submitted_by nullable to align with ORM/seed usage
    with op.batch_alter_table("requests", schema=SCHEMA) as batch_op:
        try:
            batch_op.alter_column("submitted_by", nullable=True)
        except Exception:
            # Column may already be nullable or absent
            pass


def downgrade() -> None:
    # Revert submitted_by nullability to NOT NULL
    with op.batch_alter_table("requests", schema=SCHEMA) as batch_op:
        try:
            batch_op.alter_column("submitted_by", nullable=False)
        except Exception:
            pass

    # Drop finished_at column
    op.drop_column("requests", "finished_at", schema=SCHEMA)

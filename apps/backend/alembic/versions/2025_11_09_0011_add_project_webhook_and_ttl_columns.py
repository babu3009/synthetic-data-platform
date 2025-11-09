"""
Add webhook_run_status_url and artifact_ttl_days to projects table.

This migration is schema-aware and safe to run multiple times. It uses
ADD COLUMN IF NOT EXISTS to avoid errors if columns already exist.
"""

from alembic import op
import sqlalchemy as sa

# Import dynamic schema name
try:
    from app.db.base import SCHEMA_NAME as SCHEMA
except Exception:
    SCHEMA = "synthetic_data"

# revision identifiers, used by Alembic.
revision = "2025_11_09_0011"
down_revision = "2025_11_09_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL to leverage IF NOT EXISTS for idempotency
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {SCHEMA}.projects
            ADD COLUMN IF NOT EXISTS webhook_run_status_url VARCHAR(2048)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {SCHEMA}.projects
            ADD COLUMN IF NOT EXISTS artifact_ttl_days INTEGER
            """
        )
    )


def downgrade() -> None:
    # Safe downgrades; ignore if columns are already absent
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {SCHEMA}.projects
            DROP COLUMN IF EXISTS webhook_run_status_url
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {SCHEMA}.projects
            DROP COLUMN IF EXISTS artifact_ttl_days
            """
        )
    )

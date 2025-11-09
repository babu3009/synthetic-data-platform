"""
Add uppercase OPENAI to llm_provider_kind enum for compatibility.

Some code paths or drivers may bind the enum name (OPENAI) instead of the
lowercase value (openai). This migration makes the enum tolerant by adding
the uppercase variant as an allowed value.
"""

from alembic import op


revision = "2025_11_09_0012"
down_revision = "2025_11_09_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add uppercase value to the correct enum type name used by models/migrations
    op.execute("ALTER TYPE llm_provider_kind ADD VALUE IF NOT EXISTS 'OPENAI'")


def downgrade() -> None:
    # Enum values cannot be dropped easily; no-op downgrade.
    pass

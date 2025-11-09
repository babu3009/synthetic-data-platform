"""Add uppercase OPENAI value to llmproviderkind enum for compatibility

Revision ID: 2025_11_09_0007
Revises: 2025_11_09_0006
Create Date: 2025-11-09
"""
from alembic import op


revision = "2025_11_09_0007"
down_revision = "2025_11_09_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add uppercase OPENAI value if it does not exist (case-sensitive distinct from 'openai')
    op.execute("ALTER TYPE llmproviderkind ADD VALUE IF NOT EXISTS 'OPENAI'")


def downgrade() -> None:
    # Cannot easily remove enum value in PostgreSQL; noop.
    pass

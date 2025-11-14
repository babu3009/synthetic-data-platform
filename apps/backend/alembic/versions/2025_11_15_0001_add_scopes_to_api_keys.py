"""add_scopes_to_api_keys

Revision ID: 2025_11_15_0001
Revises: 2025_11_14_2352
Create Date: 2025-11-15 00:01:00

"""
from alembic import op
import sqlalchemy as sa
from app.db.types import StringArray

# revision identifiers, used by Alembic.
revision = '2025_11_15_0001'
down_revision = '2025_11_14_2352'
branch_labels = None
depends_on = None

SCHEMA = "synthetic_data"


def upgrade() -> None:
    """Add scopes column to api_keys table."""
    op.add_column(
        'api_keys',
        sa.Column('scopes', StringArray(), nullable=False, server_default='{}'),
        schema=SCHEMA
    )


def downgrade() -> None:
    """Remove scopes column from api_keys table."""
    op.drop_column('api_keys', 'scopes', schema=SCHEMA)

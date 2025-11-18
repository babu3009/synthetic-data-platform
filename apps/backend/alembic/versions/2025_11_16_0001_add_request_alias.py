"""add_request_alias

Revision ID: 2025_11_16_0001
Revises: 2025_11_15_0240
Create Date: 2025-01-16 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_11_16_0001'
down_revision = '2025_11_15_0240'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add alias column to requests table."""
    op.add_column(
        'requests',
        sa.Column('alias', sa.String(length=255), nullable=True),
        schema='synthetic_data'
    )
    op.create_index(
        op.f('ix_synthetic_data_requests_alias'),
        'requests',
        ['alias'],
        unique=False,
        schema='synthetic_data'
    )


def downgrade() -> None:
    """Remove alias column from requests table."""
    op.drop_index(
        op.f('ix_synthetic_data_requests_alias'),
        table_name='requests',
        schema='synthetic_data'
    )
    op.drop_column('requests', 'alias', schema='synthetic_data')

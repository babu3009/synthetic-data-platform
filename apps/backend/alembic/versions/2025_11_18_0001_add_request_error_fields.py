"""add_request_error_fields

Revision ID: 2025_11_18_0001
Revises: 2025_11_16_0001
Create Date: 2025-01-18 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_11_18_0001'
down_revision = '2025_11_16_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add error_message and error_traceback columns to requests table."""
    op.add_column(
        'requests',
        sa.Column('error_message', sa.Text(), nullable=True),
        schema='synthetic_data'
    )
    op.add_column(
        'requests',
        sa.Column('error_traceback', sa.Text(), nullable=True),
        schema='synthetic_data'
    )


def downgrade() -> None:
    """Remove error tracking columns from requests table."""
    op.drop_column('requests', 'error_traceback', schema='synthetic_data')
    op.drop_column('requests', 'error_message', schema='synthetic_data')

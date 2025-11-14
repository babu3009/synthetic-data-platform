"""merge heads

Revision ID: cf11522998c9
Revises: 2025_11_14_0001, 2025_11_14_120000
Create Date: 2025-11-14 23:04:36.212647

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf11522998c9'
down_revision = ('2025_11_14_0001', '2025_11_14_120000')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
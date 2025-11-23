"""add description to wizard_entities

Revision ID: 2025_11_23_0002
Revises: 2025_11_23_0001
Create Date: 2025-11-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_11_23_0002'
down_revision = '2025_11_23_0001'
branch_labels = None
depends_on = None

SCHEMA = 'synthetic_data'


def upgrade():
    op.add_column(
        'wizard_entities',
        sa.Column('description', sa.Text(), nullable=True),
        schema=SCHEMA
    )


def downgrade():
    op.drop_column('wizard_entities', 'description', schema=SCHEMA)

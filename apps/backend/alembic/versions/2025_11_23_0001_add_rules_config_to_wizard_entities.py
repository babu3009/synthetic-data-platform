"""add rules_config to wizard_entities

Revision ID: 2025_11_23_0001
Revises: 2025_11_18_0001
Create Date: 2025-11-23 19:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_11_23_0001'
down_revision = '2025_11_18_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('wizard_entities', 
        sa.Column('rules_config', sa.Text(), nullable=True),
        schema='synthetic_data'
    )
    op.add_column('wizard_entities',
        sa.Column('rules_format', sa.String(length=10), nullable=True),
        schema='synthetic_data'
    )


def downgrade() -> None:
    op.drop_column('wizard_entities', 'rules_format', schema='synthetic_data')
    op.drop_column('wizard_entities', 'rules_config', schema='synthetic_data')

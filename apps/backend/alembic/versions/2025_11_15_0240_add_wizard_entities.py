"""add wizard_entities table

Revision ID: 2025_11_15_0240
Revises: 2025_11_15_0001
Create Date: 2025-11-15 02:40:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_11_15_0240'
down_revision = '2025_11_15_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('wizard_entities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['synthetic_data.projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='synthetic_data'
    )
    op.create_index('ix_synthetic_data_wizard_entities_name', 'wizard_entities', ['name'], unique=False, schema='synthetic_data')
    op.create_index('ix_synthetic_data_wizard_entities_project_id', 'wizard_entities', ['project_id'], unique=False, schema='synthetic_data')


def downgrade() -> None:
    op.drop_index('ix_synthetic_data_wizard_entities_project_id', table_name='wizard_entities', schema='synthetic_data')
    op.drop_index('ix_synthetic_data_wizard_entities_name', table_name='wizard_entities', schema='synthetic_data')
    op.drop_table('wizard_entities', schema='synthetic_data')

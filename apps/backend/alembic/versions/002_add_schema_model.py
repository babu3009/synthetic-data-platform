"""Add schema model for DDL ingestion

Revision ID: 002_add_schema_model
Revises: 001_initial
Create Date: 2025-11-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_schema_model'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schemas table
    op.create_table(
        'schemas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('schema_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('dag_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('warnings', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['synthetic_data.sources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id'),
        schema='synthetic_data'
    )
    
    # Create index on source_id
    op.create_index(
        op.f('ix_synthetic_data_schemas_source_id'),
        'schemas',
        ['source_id'],
        unique=False,
        schema='synthetic_data'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_synthetic_data_schemas_source_id'), table_name='schemas', schema='synthetic_data')
    
    # Drop table
    op.drop_table('schemas', schema='synthetic_data')

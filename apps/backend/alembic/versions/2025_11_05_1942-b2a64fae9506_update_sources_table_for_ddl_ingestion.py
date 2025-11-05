"""update_sources_table_for_ddl_ingestion

Revision ID: b2a64fae9506
Revises: 002_add_schema_model
Create Date: 2025-11-05 19:42:14.874965

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b2a64fae9506'
down_revision = '002_add_schema_model'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop columns that are no longer needed
    op.drop_column('sources', 'connection_details', schema='synthetic_data')
    op.drop_column('sources', 'name', schema='synthetic_data')
    op.drop_column('sources', 'schema_info', schema='synthetic_data')
    
    # Change kind column from String(50) to plain String  
    op.alter_column('sources', 'kind', 
                    type_=sa.String(length=50), 
                    existing_type=sa.String(length=50),
                    nullable=False,
                    schema='synthetic_data')
    
    # Add new columns for DDL ingestion
    op.add_column('sources', sa.Column('storage_uri', sa.String(length=2048), nullable=False), schema='synthetic_data')
    op.add_column('sources', sa.Column('checksum', sa.String(length=64), nullable=True), schema='synthetic_data')


def downgrade() -> None:
    # Drop new columns
    op.drop_column('sources', 'checksum', schema='synthetic_data')
    op.drop_column('sources', 'storage_uri', schema='synthetic_data')
    
    # Re-add old columns
    op.add_column('sources', sa.Column('schema_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='synthetic_data')
    op.add_column('sources', sa.Column('name', sa.String(length=255), nullable=False), schema='synthetic_data')
    op.add_column('sources', sa.Column('connection_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False), schema='synthetic_data')
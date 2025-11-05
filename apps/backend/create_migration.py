"""
Create initial migration manually.
"""
import asyncio
from datetime import datetime
from pathlib import Path

# Create migration file
migration_content = '''"""Add synthetic_data schema and all models

Revision ID: 001_initial
Revises: 
Create Date: {}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schema
    op.execute('CREATE SCHEMA IF NOT EXISTS synthetic_data')
    
    # Create projects table
    op.create_table('projects',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('owner', sa.String(length=255), nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_projects_name'), 'projects', ['name'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_projects_owner'), 'projects', ['owner'], unique=False, schema='synthetic_data')

    # Create sources table
    op.create_table('sources',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('connection_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('schema_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['synthetic_data.projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_sources_kind'), 'sources', ['kind'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_sources_project_id'), 'sources', ['project_id'], unique=False, schema='synthetic_data')

    # Create requests table
    op.create_table('requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('row_count', sa.Integer(), nullable=True),
    sa.Column('submitted_by', sa.String(length=255), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['synthetic_data.projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_requests_project_id'), 'requests', ['project_id'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_requests_status'), 'requests', ['status'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_requests_type'), 'requests', ['type'], unique=False, schema='synthetic_data')

    # Create configs table
    op.create_table('configs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('request_id', sa.UUID(), nullable=False),
    sa.Column('llm_provider', sa.String(length=100), nullable=False),
    sa.Column('llm_model', sa.String(length=100), nullable=False),
    sa.Column('llm_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('generation_strategy', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['synthetic_data.requests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_configs_request_id'), 'configs', ['request_id'], unique=False, schema='synthetic_data')

    # Create artifacts table
    op.create_table('artifacts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('request_id', sa.UUID(), nullable=False),
    sa.Column('format', sa.String(length=50), nullable=False),
    sa.Column('storage_path', sa.Text(), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('checksum', sa.String(length=64), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['request_id'], ['synthetic_data.requests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_artifacts_format'), 'artifacts', ['format'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_artifacts_request_id'), 'artifacts', ['request_id'], unique=False, schema='synthetic_data')

    # Create api_keys table
    op.create_table('api_keys',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('hashed_key', sa.String(length=255), nullable=False),
    sa.Column('prefix', sa.String(length=10), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['synthetic_data.projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_api_keys_hashed_key'), 'api_keys', ['hashed_key'], unique=True, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_api_keys_project_id'), 'api_keys', ['project_id'], unique=False, schema='synthetic_data')

    # Create audit_events table
    op.create_table('audit_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['synthetic_data.projects.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    schema='synthetic_data'
    )
    op.create_index(op.f('ix_synthetic_data_audit_events_action'), 'audit_events', ['action'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_audit_events_actor'), 'audit_events', ['actor'], unique=False, schema='synthetic_data')
    op.create_index(op.f('ix_synthetic_data_audit_events_project_id'), 'audit_events', ['project_id'], unique=False, schema='synthetic_data')


def downgrade() -> None:
    # Drop all tables
    op.drop_index(op.f('ix_synthetic_data_audit_events_project_id'), table_name='audit_events', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_audit_events_actor'), table_name='audit_events', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_audit_events_action'), table_name='audit_events', schema='synthetic_data')
    op.drop_table('audit_events', schema='synthetic_data')
    
    op.drop_index(op.f('ix_synthetic_data_api_keys_project_id'), table_name='api_keys', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_api_keys_hashed_key'), table_name='api_keys', schema='synthetic_data')
    op.drop_table('api_keys', schema='synthetic_data')
    
    op.drop_index(op.f('ix_synthetic_data_artifacts_request_id'), table_name='artifacts', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_artifacts_format'), table_name='artifacts', schema='synthetic_data')
    op.drop_table('artifacts', schema='synthetic_data')
    
    op.drop_index(op.f('ix_synthetic_data_configs_request_id'), table_name='configs', schema='synthetic_data')
    op.drop_table('configs', schema='synthetic_data')
    
    op.drop_index(op.f('ix_synthetic_data_requests_type'), table_name='requests', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_requests_status'), table_name='requests', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_requests_project_id'), table_name='requests', schema='synthetic_data')
    op.drop_table('requests', schema='synthetic_data')
    
    op.drop_index(op.f('ix_synthetic_data_sources_project_id'), table_name='sources', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_sources_kind'), table_name='sources', schema='synthetic_data')
    op.drop_table('sources', schema='synthetic_data')
    
    op.drop_index(op.f('ix_synthetic_data_projects_owner'), table_name='projects', schema='synthetic_data')
    op.drop_index(op.f('ix_synthetic_data_projects_name'), table_name='projects', schema='synthetic_data')
    op.drop_table('projects', schema='synthetic_data')
    
    # Drop schema
    op.execute('DROP SCHEMA IF EXISTS synthetic_data CASCADE')
'''.format(datetime.now().isoformat())

# Write migration file
versions_dir = Path(__file__).parent / "alembic" / "versions"
versions_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")
filename = f"{timestamp}-001_initial-add_synthetic_data_schema_and_all_models.py"
filepath = versions_dir / filename

with open(filepath, "w") as f:
    f.write(migration_content)

print(f"✓ Created migration: {filename}")
print(f"  Location: {filepath}")
print("\nNext step: Run 'alembic upgrade head' to apply the migration")

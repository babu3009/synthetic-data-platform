"""Add schema and all models (schema resolved at runtime)

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-05T17:35:10.633725

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from app.db.base import SCHEMA_NAME  # dynamic target schema

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schema
    op.execute(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}')
    
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
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_projects_name'), 'projects', ['name'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_projects_owner'), 'projects', ['owner'], unique=False, schema=SCHEMA_NAME)

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
    sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA_NAME}.projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_sources_kind'), 'sources', ['kind'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_sources_project_id'), 'sources', ['project_id'], unique=False, schema=SCHEMA_NAME)

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
    sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA_NAME}.projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_requests_project_id'), 'requests', ['project_id'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_requests_status'), 'requests', ['status'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_requests_type'), 'requests', ['type'], unique=False, schema=SCHEMA_NAME)

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
    sa.ForeignKeyConstraint(['request_id'], [f'{SCHEMA_NAME}.requests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_configs_request_id'), 'configs', ['request_id'], unique=False, schema=SCHEMA_NAME)

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
    sa.ForeignKeyConstraint(['request_id'], [f'{SCHEMA_NAME}.requests.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_artifacts_format'), 'artifacts', ['format'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_artifacts_request_id'), 'artifacts', ['request_id'], unique=False, schema=SCHEMA_NAME)

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
    sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA_NAME}.projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_api_keys_hashed_key'), 'api_keys', ['hashed_key'], unique=True, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_api_keys_project_id'), 'api_keys', ['project_id'], unique=False, schema=SCHEMA_NAME)

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
    sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA_NAME}.projects.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA_NAME
    )
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_audit_events_action'), 'audit_events', ['action'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_audit_events_actor'), 'audit_events', ['actor'], unique=False, schema=SCHEMA_NAME)
    op.create_index(op.f(f'ix_{SCHEMA_NAME}_audit_events_project_id'), 'audit_events', ['project_id'], unique=False, schema=SCHEMA_NAME)


def downgrade() -> None:
    # Drop all tables
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_audit_events_project_id'), table_name='audit_events', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_audit_events_actor'), table_name='audit_events', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_audit_events_action'), table_name='audit_events', schema=SCHEMA_NAME)
    op.drop_table('audit_events', schema=SCHEMA_NAME)
    
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_api_keys_project_id'), table_name='api_keys', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_api_keys_hashed_key'), table_name='api_keys', schema=SCHEMA_NAME)
    op.drop_table('api_keys', schema=SCHEMA_NAME)
    
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_artifacts_request_id'), table_name='artifacts', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_artifacts_format'), table_name='artifacts', schema=SCHEMA_NAME)
    op.drop_table('artifacts', schema=SCHEMA_NAME)
    
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_configs_request_id'), table_name='configs', schema=SCHEMA_NAME)
    op.drop_table('configs', schema=SCHEMA_NAME)
    
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_requests_type'), table_name='requests', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_requests_status'), table_name='requests', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_requests_project_id'), table_name='requests', schema=SCHEMA_NAME)
    op.drop_table('requests', schema=SCHEMA_NAME)
    
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_sources_project_id'), table_name='sources', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_sources_kind'), table_name='sources', schema=SCHEMA_NAME)
    op.drop_table('sources', schema=SCHEMA_NAME)
    
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_projects_owner'), table_name='projects', schema=SCHEMA_NAME)
    op.drop_index(op.f(f'ix_{SCHEMA_NAME}_projects_name'), table_name='projects', schema=SCHEMA_NAME)
    op.drop_table('projects', schema=SCHEMA_NAME)
    
    # Drop schema
    op.execute(f'DROP SCHEMA IF EXISTS {SCHEMA_NAME} CASCADE')

"""Add LLM provider/credential/model and project settings tables

Revision ID: 2025_11_07_0001
Revises: 2025_11_05_1942-b2a64fae9506_update_sources_table_for_ddl_ingestion
Create Date: 2025-11-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_11_07_0001'
# Chain after last known migration revision id
down_revision = 'b2a64fae9506'
branch_labels = None
depends_on = None

from app.db.base import SCHEMA_NAME as SCHEMA  # dynamic schema resolution

# We'll avoid binding the Enum directly to the column during table creation to prevent auto CREATE TYPE
ENUM_NAME = 'llm_provider_kind'
ENUM_VALUES = ("openai", "anthropic", "ollama", "lmstudio", "custom")


def upgrade() -> None:
    # Ensure the enum type exists using a guarded DO block (works even without IF NOT EXISTS)
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                BEGIN
                    CREATE TYPE llm_provider_kind AS ENUM ('openai','anthropic','ollama','lmstudio','custom');
                EXCEPTION WHEN duplicate_object THEN
                    NULL;
                END;
            END$$;
            """
        )
    )

    # llm_providers
    op.create_table(
        'llm_providers',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        # Create as VARCHAR first; we will ALTER to enum after table creation
        sa.Column('kind', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('base_url', sa.String(length=1024), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_llm_providers_kind', 'llm_providers', ['kind'], unique=False, schema=SCHEMA)
    op.create_index('uq_llm_providers_name', 'llm_providers', ['name'], unique=True, schema=SCHEMA)

    # Convert kind column to enum type (now that type exists)
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA}.llm_providers ALTER COLUMN kind TYPE {ENUM_NAME} USING kind::{ENUM_NAME}"
        )
    )

    # llm_credentials
    op.create_table(
        'llm_credentials',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enc_payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], [f'{SCHEMA}.llm_providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_llm_credentials_provider_id', 'llm_credentials', ['provider_id'], unique=False, schema=SCHEMA)

    # llm_models
    op.create_table(
        'llm_models',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('context_tokens', sa.Integer(), nullable=True),
        sa.Column('supports_json', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], [f'{SCHEMA}.llm_providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_llm_models_provider_id', 'llm_models', ['provider_id'], unique=False, schema=SCHEMA)
    op.create_index('ix_llm_models_name', 'llm_models', ['name'], unique=False, schema=SCHEMA)

    # project_llm_settings
    op.create_table(
        'project_llm_settings',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('provider_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('model_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('guardrails_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA}.projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_id'], [f'{SCHEMA}.llm_providers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_id'], [f'{SCHEMA}.llm_models.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_project_llm_settings_project_id', 'project_llm_settings', ['project_id'], unique=False, schema=SCHEMA)


def downgrade() -> None:
    op.drop_index('ix_project_llm_settings_project_id', table_name='project_llm_settings', schema=SCHEMA)
    op.drop_table('project_llm_settings', schema=SCHEMA)

    op.drop_index('ix_llm_models_name', table_name='llm_models', schema=SCHEMA)
    op.drop_index('ix_llm_models_provider_id', table_name='llm_models', schema=SCHEMA)
    op.drop_table('llm_models', schema=SCHEMA)

    op.drop_index('ix_llm_credentials_provider_id', table_name='llm_credentials', schema=SCHEMA)
    op.drop_table('llm_credentials', schema=SCHEMA)

    op.drop_index('uq_llm_providers_name', table_name='llm_providers', schema=SCHEMA)
    op.drop_index('ix_llm_providers_kind', table_name='llm_providers', schema=SCHEMA)
    op.drop_table('llm_providers', schema=SCHEMA)

    # Drop enum type only if exists (safe)
    # Leave enum type in place (shared); do not drop to avoid impacting other schemas
    return

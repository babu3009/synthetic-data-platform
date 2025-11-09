"""Add missing LLM tables (llm_providers, llm_credentials, llm_models, project_llm_settings)

Revision ID: 2025_11_09_0006
Revises: 2025_11_09_0005
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "2025_11_09_0006"
down_revision = "2025_11_09_0005"
branch_labels = None
depends_on = None

from app.db.base import SCHEMA_NAME as SCHEMA
assert isinstance(SCHEMA, str) and SCHEMA, "SCHEMA must be a non-empty string"

# Avoid enum auto-create; we'll add kind as VARCHAR then alter if needed.
ENUM_NAME = "llm_provider_kind"
ENUM_VALUES = ("openai", "anthropic", "ollama", "lmstudio", "custom")


def _table_exists(bind, schema: str, table: str) -> bool:
    res = bind.execute(
        sa.text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    )
    return res.scalar() is not None


def upgrade() -> None:
    bind = op.get_bind()
    # If primary LLM tables already exist (from earlier migration), skip this compatibility migration
    if _table_exists(bind, SCHEMA, "llm_providers"):
        return
    # Enum type assumed to exist (created previously by ORM/migration); skipping creation to avoid DuplicateObjectError.

    # llm_providers
    op.create_table(
        "llm_providers",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=1024), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_llm_providers_kind", "llm_providers", ["kind"], unique=False, schema=SCHEMA)
    # Attempt enum creation guarded; then convert column
    op.execute(sa.text("""
    DO $$
    BEGIN
        BEGIN
            CREATE TYPE llm_provider_kind AS ENUM ('openai','anthropic','ollama','lmstudio','custom');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END;
    END$$;"""))
    op.execute(sa.text(f"ALTER TABLE {SCHEMA}.llm_providers ALTER COLUMN kind TYPE llm_provider_kind USING kind::llm_provider_kind"))
    op.create_index(
        "uq_llm_providers_name", "llm_providers", ["name"], unique=True, schema=SCHEMA
    )

    # llm_credentials
    op.create_table(
        "llm_credentials",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("enc_payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"], [f"{SCHEMA}.llm_providers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_llm_credentials_provider_id",
        "llm_credentials",
        ["provider_id"],
        unique=False,
        schema=SCHEMA,
    )

    # llm_models
    op.create_table(
        "llm_models",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("context_tokens", sa.Integer(), nullable=True),
        sa.Column("supports_json", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], [f"{SCHEMA}.llm_providers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_llm_models_provider_id", "llm_models", ["provider_id"], unique=False, schema=SCHEMA
    )
    op.create_index(
        "ix_llm_models_name", "llm_models", ["name"], unique=False, schema=SCHEMA
    )

    # project_llm_settings
    op.create_table(
        "project_llm_settings",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("model_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "guardrails_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], [f"{SCHEMA}.projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], [f"{SCHEMA}.llm_providers.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["model_id"], [f"{SCHEMA}.llm_models.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_project_llm_settings_project_id",
        "project_llm_settings",
        ["project_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_llm_settings_project_id",
        table_name="project_llm_settings",
        schema=SCHEMA,
    )
    op.drop_table("project_llm_settings", schema=SCHEMA)

    op.drop_index("ix_llm_models_name", table_name="llm_models", schema=SCHEMA)
    op.drop_index(
        "ix_llm_models_provider_id", table_name="llm_models", schema=SCHEMA
    )
    op.drop_table("llm_models", schema=SCHEMA)

    op.drop_index(
        "ix_llm_credentials_provider_id", table_name="llm_credentials", schema=SCHEMA
    )
    op.drop_table("llm_credentials", schema=SCHEMA)

    op.drop_index("uq_llm_providers_name", table_name="llm_providers", schema=SCHEMA)
    op.drop_index("ix_llm_providers_kind", table_name="llm_providers", schema=SCHEMA)
    op.drop_table("llm_providers", schema=SCHEMA)

    # Do not drop enum type (may be shared with ORM); leaving intact.

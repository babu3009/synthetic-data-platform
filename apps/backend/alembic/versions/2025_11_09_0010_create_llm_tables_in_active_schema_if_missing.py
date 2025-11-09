"""Create LLM tables in active schema when not synthetic_data (idempotent)

Revision ID: 2025_11_09_0010
Revises: 2025_11_09_0008
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2025_11_09_0010"
down_revision = "2025_11_09_0008"
branch_labels = None
depends_on = None

# Resolve active schema dynamically
from app.db.base import SCHEMA_NAME as ACTIVE_SCHEMA  # type: ignore

# Ensure ACTIVE_SCHEMA is a concrete string (avoid Optional type noise for type checkers)
assert isinstance(ACTIVE_SCHEMA, str) and ACTIVE_SCHEMA, "ACTIVE_SCHEMA must be a non-empty string"
ACTIVE_SCHEMA_NAME = ACTIVE_SCHEMA

SOURCE_SCHEMA = "synthetic_data"


provider_kind_enum = sa.Enum(
    "openai", "anthropic", "ollama", "lmstudio", "custom", name="llm_provider_kind", create_type=False
)


def _table_exists(bind, schema: str, table: str) -> bool:
    res = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    )
    return res.scalar() is not None


def _column_uses_enum(bind, schema: str, table: str, column: str, enum_name: str) -> bool:
    res = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
              AND column_name = :column
              AND udt_name = :enum_name
            """
        ),
        {"schema": schema, "table": table, "column": column, "enum_name": enum_name},
    )
    return res.scalar() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # Only act when targeting a non-default schema
    if ACTIVE_SCHEMA_NAME == SOURCE_SCHEMA:
        return

    # Enum type is global; assume it already exists from primary schema migrations.
    # If running in isolated environment and missing, attempt creation guarded.
    # Ensure global enum type exists (idempotent)
    try:
        provider_kind_enum.create(bind, checkfirst=True)
    except Exception:
        pass

    # llm_providers
    if not _table_exists(bind, ACTIVE_SCHEMA_NAME, "llm_providers"):
        op.create_table(
            "llm_providers",
            sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
            # Create as TEXT first to avoid auto-creating enum; cast to enum after
            sa.Column("kind", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("base_url", sa.String(length=1024), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            schema=ACTIVE_SCHEMA_NAME,
        )
        op.create_index("ix_llm_providers_kind", "llm_providers", ["kind"], unique=False, schema=ACTIVE_SCHEMA_NAME)
        op.create_index("uq_llm_providers_name", "llm_providers", ["name"], unique=True, schema=ACTIVE_SCHEMA_NAME)
        # Convert kind column to enum type if available
        op.execute(
            sa.text(
                f"ALTER TABLE {ACTIVE_SCHEMA_NAME}.llm_providers ALTER COLUMN kind TYPE llm_provider_kind USING kind::llm_provider_kind"
            )
        )
    else:
        # Table exists (possibly from partial failed migration); ensure kind column is enum
        if not _column_uses_enum(bind, ACTIVE_SCHEMA_NAME, "llm_providers", "kind", "llm_provider_kind"):
            try:
                op.execute(
                    sa.text(
                        f"ALTER TABLE {ACTIVE_SCHEMA_NAME}.llm_providers ALTER COLUMN kind TYPE llm_provider_kind USING kind::llm_provider_kind"
                    )
                )
            except Exception:
                # Leave as-is if conversion fails; subsequent code can still run
                pass

    # llm_credentials
    if not _table_exists(bind, ACTIVE_SCHEMA_NAME, "llm_credentials"):
        op.create_table(
            "llm_credentials",
            sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
            sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=False),
            sa.Column("enc_payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["provider_id"], [f"{ACTIVE_SCHEMA_NAME}.llm_providers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            schema=ACTIVE_SCHEMA_NAME,
        )
        op.create_index("ix_llm_credentials_provider_id", "llm_credentials", ["provider_id"], unique=False, schema=ACTIVE_SCHEMA_NAME)

    # llm_models
    if not _table_exists(bind, ACTIVE_SCHEMA_NAME, "llm_models"):
        op.create_table(
            "llm_models",
            sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
            sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("context_tokens", sa.Integer(), nullable=True),
            sa.Column("supports_json", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["provider_id"], [f"{ACTIVE_SCHEMA_NAME}.llm_providers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            schema=ACTIVE_SCHEMA_NAME,
        )
        op.create_index("ix_llm_models_provider_id", "llm_models", ["provider_id"], unique=False, schema=ACTIVE_SCHEMA_NAME)
        op.create_index("ix_llm_models_name", "llm_models", ["name"], unique=False, schema=ACTIVE_SCHEMA_NAME)

    # project_llm_settings
    if not _table_exists(bind, ACTIVE_SCHEMA_NAME, "project_llm_settings"):
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
            sa.Column("guardrails_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], [f"{ACTIVE_SCHEMA_NAME}.projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["provider_id"], [f"{ACTIVE_SCHEMA_NAME}.llm_providers.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["model_id"], [f"{ACTIVE_SCHEMA_NAME}.llm_models.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            schema=ACTIVE_SCHEMA_NAME,
        )
        op.create_index("ix_project_llm_settings_project_id", "project_llm_settings", ["project_id"], unique=False, schema=ACTIVE_SCHEMA_NAME)


def downgrade() -> None:
    # Only act when targeting a non-default schema
    if ACTIVE_SCHEMA_NAME == SOURCE_SCHEMA:
        return

    # Drop in reverse order of dependencies
    op.drop_index("ix_project_llm_settings_project_id", table_name="project_llm_settings", schema=ACTIVE_SCHEMA_NAME)
    op.drop_table("project_llm_settings", schema=ACTIVE_SCHEMA_NAME)

    op.drop_index("ix_llm_models_name", table_name="llm_models", schema=ACTIVE_SCHEMA_NAME)
    op.drop_index("ix_llm_models_provider_id", table_name="llm_models", schema=ACTIVE_SCHEMA_NAME)
    op.drop_table("llm_models", schema=ACTIVE_SCHEMA_NAME)

    op.drop_index("ix_llm_credentials_provider_id", table_name="llm_credentials", schema=ACTIVE_SCHEMA_NAME)
    op.drop_table("llm_credentials", schema=ACTIVE_SCHEMA_NAME)

    op.drop_index("uq_llm_providers_name", table_name="llm_providers", schema=ACTIVE_SCHEMA_NAME)
    op.drop_index("ix_llm_providers_kind", table_name="llm_providers", schema=ACTIVE_SCHEMA_NAME)
    op.drop_table("llm_providers", schema=ACTIVE_SCHEMA_NAME)

    # Do not drop the enum to avoid affecting other schemas

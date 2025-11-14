"""Add per-task default mapping for LLM provider

Revision ID: 2025_11_13_0015
Revises: 2025_11_12_0014
Create Date: 2025-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2025_11_13_0015"
down_revision = "2025_11_12_0014"
branch_labels = None
depends_on = None

from app.db.base import SCHEMA_NAME as SCHEMA  # type: ignore


def upgrade() -> None:
    # Ensure the enum type exists via guarded DO block
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                BEGIN
                    CREATE TYPE llm_task_type AS ENUM ('chat','embeddings','tools');
                EXCEPTION WHEN duplicate_object THEN
                    NULL;
                END;
            END$$;
            """
        )
    )

    # Create llm_provider_task_defaults table
    op.create_table(
        "llm_provider_task_defaults",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=False),
        # Create as VARCHAR first; alter to enum after table creation to avoid auto CREATE TYPE
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("model_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], [f"{SCHEMA}.llm_providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], [f"{SCHEMA}.llm_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    # Convert column to enum type now that type exists
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA}.llm_provider_task_defaults ALTER COLUMN task_type TYPE llm_task_type USING task_type::llm_task_type"
        )
    )
    op.create_index(
        "ix_llm_provider_task_defaults_provider_id",
        "llm_provider_task_defaults",
        ["provider_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_llm_provider_task_defaults_task_type",
        "llm_provider_task_defaults",
        ["task_type"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_llm_provider_task_defaults_model_id",
        "llm_provider_task_defaults",
        ["model_id"],
        unique=False,
        schema=SCHEMA,
    )
    # Enforce one default per (provider, task_type)
    op.create_index(
        "uq_llm_provider_task_default_per_task",
        "llm_provider_task_defaults",
        ["provider_id", "task_type"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_llm_provider_task_default_per_task",
        table_name="llm_provider_task_defaults",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_llm_provider_task_defaults_model_id",
        table_name="llm_provider_task_defaults",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_llm_provider_task_defaults_task_type",
        table_name="llm_provider_task_defaults",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_llm_provider_task_defaults_provider_id",
        table_name="llm_provider_task_defaults",
        schema=SCHEMA,
    )
    op.drop_table("llm_provider_task_defaults", schema=SCHEMA)
    # Intentionally keep enum type to avoid impacting other revisions; do not drop llm_task_type here

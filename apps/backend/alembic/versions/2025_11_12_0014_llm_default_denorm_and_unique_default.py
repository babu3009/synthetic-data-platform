"""Add default_model_id and enforce single default per provider

Revision ID: 2025_11_12_0014
Revises: 2025_11_09_1013
Create Date: 2025-11-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2025_11_12_0014"
down_revision = "2025_11_09_1013"
branch_labels = None
depends_on = None

# Use the app's configured schema
from app.db.base import SCHEMA_NAME as SCHEMA  # type: ignore


def upgrade() -> None:
    # 1) Add denormalized default_model_id to llm_providers (nullable)
    with op.batch_alter_table("llm_providers", schema=SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("default_model_id", sa.UUID(as_uuid=True), nullable=True))
    # Add FK constraint separately to avoid batch limitations
    op.create_foreign_key(
        constraint_name="fk_llm_providers_default_model_id",
        source_table="llm_providers",
        referent_table="llm_models",
        local_cols=["default_model_id"],
        remote_cols=["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )
    # Optional index for quick lookup
    op.create_index(
        "ix_llm_providers_default_model_id", "llm_providers", ["default_model_id"], unique=False, schema=SCHEMA
    )

    # 2) Enforce at most one default model per provider via partial unique index
    #    This ensures (provider_id) is unique among rows where is_default=true
    op.create_index(
        "uq_llm_models_default_per_provider",
        "llm_models",
        ["provider_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("is_default")
    )


def downgrade() -> None:
    # Drop partial unique index
    op.drop_index("uq_llm_models_default_per_provider", table_name="llm_models", schema=SCHEMA)

    # Drop index and FK, then column
    op.drop_index("ix_llm_providers_default_model_id", table_name="llm_providers", schema=SCHEMA)
    op.drop_constraint("fk_llm_providers_default_model_id", "llm_providers", type_="foreignkey", schema=SCHEMA)
    with op.batch_alter_table("llm_providers", schema=SCHEMA) as batch_op:
        batch_op.drop_column("default_model_id")

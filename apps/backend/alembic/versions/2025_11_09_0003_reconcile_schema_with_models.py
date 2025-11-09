"""Reconcile DB schema with ORM models (requests.seed, artifacts.storage_uri, configs columns)

Revision ID: 2025_11_09_0003
Revises: 2025_11_08_0002
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "2025_11_09_0003"
down_revision = "2025_11_08_0002"
branch_labels = None
depends_on = None

SCHEMA = "synthetic_data"


def upgrade() -> None:
    # 1) requests.seed column
    op.add_column(
        "requests",
        sa.Column("seed", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )

    # 2) artifacts.storage_path -> storage_uri
    with op.batch_alter_table("artifacts", schema=SCHEMA) as batch_op:
        batch_op.alter_column("storage_path", new_column_name="storage_uri")

    # 3) configs: add version/body_json and relax legacy columns to nullable
    op.add_column(
        "configs",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        schema=SCHEMA,
    )
    op.add_column(
        "configs",
        sa.Column(
            "body_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema=SCHEMA,
    )

    with op.batch_alter_table("configs", schema=SCHEMA) as batch_op:
        for col in ("llm_provider", "llm_model", "generation_strategy"):
            try:
                batch_op.alter_column(col, nullable=True)
            except Exception:
                # Column may already be nullable or absent; ignore
                pass


def downgrade() -> None:
    # Reverse configs adjustments
    with op.batch_alter_table("configs", schema=SCHEMA) as batch_op:
        for col in ("llm_provider", "llm_model", "generation_strategy"):
            try:
                batch_op.alter_column(col, nullable=False)
            except Exception:
                pass

    op.drop_column("configs", "body_json", schema=SCHEMA)
    op.drop_column("configs", "version", schema=SCHEMA)

    # Reverse artifacts rename
    with op.batch_alter_table("artifacts", schema=SCHEMA) as batch_op:
        batch_op.alter_column("storage_uri", new_column_name="storage_path")

    # Drop requests.seed
    op.drop_column("requests", "seed", schema=SCHEMA)

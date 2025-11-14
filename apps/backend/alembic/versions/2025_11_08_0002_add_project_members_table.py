"""Add project_members table

Revision ID: 2025_11_08_0002
Revises: 2025_11_07_0001_add_llm_tables
Create Date: 2025-11-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from app.db.base import SCHEMA_NAME

# revision identifiers, used by Alembic.
revision = "2025_11_08_0002"
down_revision = "2025_11_07_0001"
branch_labels = None
depends_on = None

SCHEMA = SCHEMA_NAME

# Define enum for project member roles
# Use create_type=False to avoid implicit creation during table create; we will
# explicitly create with checkfirst to prevent duplicate-type errors.
project_role_enum = sa.Enum(
    "OWNER",
    "EDITOR",
    "VIEWER",
    name="project_role",
    create_type=False,
)


def upgrade() -> None:
    # Ensure enum type exists (idempotent)
    bind = op.get_bind()
    project_role_enum.create(bind, checkfirst=True)

    # Create table without binding the enum to avoid auto CREATE TYPE during DDL
    op.create_table(
        "project_members",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        # temporary as String; we'll alter to enum after create
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], [f"{SCHEMA}.projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # Convert column to enum type explicitly (safe if type already exists)
    op.execute(
        text(
            f"ALTER TABLE {SCHEMA}.project_members "
            f"ALTER COLUMN role TYPE project_role USING role::text::project_role"
        )
    )

    # Indexes for efficient lookups
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"], unique=False, schema=SCHEMA)
    op.create_index("ix_project_members_user_sub", "project_members", ["user_sub"], unique=False, schema=SCHEMA)
    op.create_index("ix_project_members_role", "project_members", ["role"], unique=False, schema=SCHEMA)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_project_members_role", table_name="project_members", schema=SCHEMA)
    op.drop_index("ix_project_members_user_sub", table_name="project_members", schema=SCHEMA)
    op.drop_index("ix_project_members_project_id", table_name="project_members", schema=SCHEMA)

    # Drop table
    op.drop_table("project_members", schema=SCHEMA)

    # Drop enum type
    project_role_enum.drop(op.get_bind(), checkfirst=True)

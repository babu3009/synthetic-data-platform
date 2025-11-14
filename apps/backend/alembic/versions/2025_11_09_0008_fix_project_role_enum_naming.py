"""Fix project_members.role enum type name mismatch (create projectrole)

Revision ID: 2025_11_09_0008
Revises: 2025_11_09_0007
Create Date: 2025-11-09
"""
from alembic import op
import sqlalchemy as sa
from app.db.base import SCHEMA_NAME

revision = "2025_11_09_0008"
down_revision = "2025_11_09_0007"
branch_labels = None
depends_on = None

SCHEMA = SCHEMA_NAME

project_role_enum_correct = sa.Enum(
    "OWNER", "EDITOR", "VIEWER", name="projectrole", create_type=False
)


def upgrade() -> None:
    # Create missing enum type 'projectrole' if not present
    bind = op.get_bind()
    project_role_enum_correct.create(bind, checkfirst=True)

    # Alter column to use the new enum type expected by ORM (projectrole)
    op.execute(
        f"ALTER TABLE {SCHEMA}.project_members ALTER COLUMN role TYPE projectrole USING role::text::projectrole"
    )


def downgrade() -> None:
    # Revert column back to previous 'project_role' type if it exists
    op.execute(
        f"ALTER TABLE {SCHEMA}.project_members ALTER COLUMN role TYPE project_role USING role::text::project_role"
    )
    # (Keep 'projectrole' type; dropping enum types safely requires ensuring no dependencies.)
    # No drop executed to avoid issues if data still references 'projectrole'.

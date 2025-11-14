"""
Enforce user-id linkage and drop legacy subject column for project_members.

Revision ID: 2025_11_13_111200
Revises: 2025_11_13_105000
Create Date: 2025-11-13 11:12:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2025_11_13_111200"
down_revision = "2025_11_13_105000"
branch_labels = None
depends_on = None

from app.db.base import SCHEMA_NAME as SCHEMA  # type: ignore


def upgrade() -> None:
    # Ensure residual backfill (defensive)
    conn = op.get_bind()
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.project_members pm
        SET user_id = u.id
        FROM {SCHEMA}.users u
        WHERE pm.user_id IS NULL AND LOWER(u.email) = LOWER(pm.user_sub)
        """
    )

    # As a fallback, assign unresolved memberships to the project owner
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.project_members pm
        SET user_id = p.owner_user_id
        FROM {SCHEMA}.projects p
        WHERE pm.user_id IS NULL AND pm.project_id = p.id AND p.owner_user_id IS NOT NULL
        """
    )

    # Final fallback: assign to a system user for any remaining nulls
    # Ensure system user exists
    sys_user_rs = conn.exec_driver_sql(
        f"""
        INSERT INTO {SCHEMA}.users (id, email, password_hash, role, status)
        VALUES (gen_random_uuid(), 'legacy@system.local', '!', 'ADMIN', 'APPROVED')
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING id
        """
    )
    sys_user_id = sys_user_rs.fetchone()[0]
    # Backfill projects.owner_user_id if still null
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.projects p
        SET owner_user_id = u.id
        FROM {SCHEMA}.users u
        WHERE p.owner_user_id IS NULL AND LOWER(u.email) = LOWER(p.owner)
        """
    )
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.projects p
        SET owner_user_id = '{'{'}sys_user_id{'}'}'
        WHERE p.owner_user_id IS NULL
        """.replace("{sys_user_id}", str(sys_user_id))
    )
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.project_members pm
        SET user_id = '{'{'}sys_user_id{'}'}'
        WHERE pm.user_id IS NULL
        """.replace("{sys_user_id}", str(sys_user_id))
    )

    # Enforce NOT NULL on user_id and drop legacy user_sub
    op.alter_column("project_members", "user_id", schema=SCHEMA, existing_type=sa.UUID(), nullable=False)
    op.drop_column("project_members", "user_sub", schema=SCHEMA)

    # Enforce NOT NULL for projects.owner_user_id (keep legacy owner column for now)
    op.alter_column("projects", "owner_user_id", schema=SCHEMA, existing_type=sa.UUID(), nullable=False)


def downgrade() -> None:
    # Allow NULLs again
    op.alter_column("projects", "owner_user_id", schema=SCHEMA, existing_type=sa.UUID(), nullable=True)

    # Recreate legacy column user_sub as nullable string and backfill from users by id
    op.add_column("project_members", sa.Column("user_sub", sa.String(length=255), nullable=True), schema=SCHEMA)
    conn = op.get_bind()
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.project_members pm
        SET user_sub = u.email
        FROM {SCHEMA}.users u
        WHERE pm.user_id = u.id
        """
    )
    op.alter_column("project_members", "user_id", schema=SCHEMA, existing_type=sa.UUID(), nullable=True)

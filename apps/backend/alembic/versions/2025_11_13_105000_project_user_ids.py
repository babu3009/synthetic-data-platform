"""
Add user ID foreign keys for projects and project_members, and backfill from emails.

Revision ID: 2025_11_13_105000
Revises: 2025_11_13_0015
Create Date: 2025-11-13 10:50:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_11_13_105000'
down_revision = '2025_11_13_0015'
branch_labels = None
depends_on = None

from app.db.base import SCHEMA_NAME as SCHEMA  # type: ignore


def upgrade() -> None:
    # Add new columns
    op.add_column(
        'projects',
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index('ix_projects_owner_user_id', 'projects', ['owner_user_id'], unique=False, schema=SCHEMA)
    op.create_foreign_key(
        'fk_projects_owner_user_id_users',
        'projects', 'users', ['owner_user_id'], ['id'],
        source_schema=SCHEMA, referent_schema=SCHEMA,
    )

    op.add_column(
        'project_members',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'], unique=False, schema=SCHEMA)
    op.create_foreign_key(
        'fk_project_members_user_id_users',
        'project_members', 'users', ['user_id'], ['id'],
        source_schema=SCHEMA, referent_schema=SCHEMA,
    )

    # Backfill from emails (case-insensitive)
    conn = op.get_bind()
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.projects p
        SET owner_user_id = u.id
        FROM {SCHEMA}.users u
        WHERE LOWER(u.email) = LOWER(p.owner)
        AND p.owner_user_id IS NULL
        """
    )
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.project_members pm
        SET user_id = u.id
        FROM {SCHEMA}.users u
        WHERE LOWER(u.email) = LOWER(pm.user_sub)
        AND pm.user_id IS NULL
        """
    )

    # Note: We intentionally keep columns nullable in this migration to avoid failures
    # for records without corresponding users yet. A future migration can enforce NOT NULL
    # and drop the legacy email columns after data alignment.


def downgrade() -> None:
    # Drop FKs and columns (reverse order)
    op.drop_constraint('fk_project_members_user_id_users', 'project_members', schema=SCHEMA, type_='foreignkey')
    op.drop_index('ix_project_members_user_id', table_name='project_members', schema=SCHEMA)
    op.drop_column('project_members', 'user_id', schema=SCHEMA)

    op.drop_constraint('fk_projects_owner_user_id_users', 'projects', schema=SCHEMA, type_='foreignkey')
    op.drop_index('ix_projects_owner_user_id', table_name='projects', schema=SCHEMA)
    op.drop_column('projects', 'owner_user_id', schema=SCHEMA)

"""
Drop legacy projects.owner column after enforcing owner_user_id.

Revision ID: 2025_11_13_112500
Revises: 2025_11_13_111200
Create Date: 2025-11-13 11:25:00
"""
from alembic import op
import sqlalchemy as sa

revision = "2025_11_13_112500"
down_revision = "2025_11_13_111200"
branch_labels = None
depends_on = None

from app.db.base import SCHEMA_NAME as SCHEMA  # type: ignore


def upgrade() -> None:
    # Column projects.owner is no longer authoritative; owner_user_id is enforced NOT NULL.
    # Drop the legacy string column.
    with op.batch_alter_table("projects", schema=SCHEMA) as batch_op:
        batch_op.drop_column("owner")


def downgrade() -> None:
    # Recreate legacy column as nullable and backfill from owner_user_id -> users.email for compatibility.
    with op.batch_alter_table("projects", schema=SCHEMA) as batch_op:
        batch_op.add_column(sa.Column("owner", sa.String(length=255), nullable=True))

    conn = op.get_bind()
    conn.exec_driver_sql(
        f"""
        UPDATE {SCHEMA}.projects p
        SET owner = u.email
        FROM {SCHEMA}.users u
        WHERE p.owner IS NULL AND p.owner_user_id = u.id
        """
    )

"""Add users, email_otps tables and extend audit_events with actor_user_id

Revision ID: 2025_11_09_1013
Revises: 2025_11_09_0012
Create Date: 2025-11-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

try:
    from app.db.base import SCHEMA_NAME as SCHEMA
except Exception:  # pragma: no cover
    SCHEMA = "synthetic_data"

revision = "2025_11_09_1013"
down_revision = "2025_11_09_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres lacks CREATE TYPE IF NOT EXISTS for enums; emulate with DO blocks
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
            CREATE TYPE userrole AS ENUM ('USER','ADMIN');
        END IF;
    END $$;
    """)
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstatus') THEN
            CREATE TYPE userstatus AS ENUM ('PENDING_EMAIL_VERIFICATION','PENDING_ADMIN_APPROVAL','APPROVED','REJECTED');
        END IF;
    END $$;
    """)
    op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'emailotppurpose') THEN
            CREATE TYPE emailotppurpose AS ENUM ('email_verify','forgot_pwd','change_pwd');
        END IF;
    END $$;
    """)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(255)),
        sa.Column("role", sa.String(32), nullable=False, server_default="USER"),
        sa.Column("status", sa.String(48), nullable=False, server_default="PENDING_EMAIL_VERIFICATION"),
        sa.Column("profile_image_url", sa.String(1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        schema=SCHEMA,
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema=SCHEMA)

    op.create_table(
        "email_otps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("otp_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], ondelete="CASCADE"),
        schema=SCHEMA,
    )
    op.create_index("ix_email_otps_user_id", "email_otps", ["user_id"], schema=SCHEMA)
    op.create_index("ix_email_otps_purpose", "email_otps", ["purpose"], schema=SCHEMA)

    # Extend audit_events (actor_user_id)
    op.add_column(
        "audit_events",
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )

    # Cast string columns to enum types for strong typing (drop defaults first)
    op.execute(f"ALTER TABLE {SCHEMA}.users ALTER COLUMN role DROP DEFAULT")
    op.execute(f"ALTER TABLE {SCHEMA}.users ALTER COLUMN role TYPE userrole USING role::userrole")
    op.execute(f"ALTER TABLE {SCHEMA}.users ALTER COLUMN role SET DEFAULT 'USER'::userrole")
    op.execute(f"ALTER TABLE {SCHEMA}.users ALTER COLUMN status DROP DEFAULT")
    op.execute(f"ALTER TABLE {SCHEMA}.users ALTER COLUMN status TYPE userstatus USING status::userstatus")
    op.execute(f"ALTER TABLE {SCHEMA}.users ALTER COLUMN status SET DEFAULT 'PENDING_EMAIL_VERIFICATION'::userstatus")
    op.execute(f"ALTER TABLE {SCHEMA}.email_otps ALTER COLUMN purpose TYPE emailotppurpose USING purpose::emailotppurpose")


def downgrade() -> None:
    op.drop_column("audit_events", "actor_user_id", schema=SCHEMA)
    op.drop_index("ix_email_otps_purpose", table_name="email_otps", schema=SCHEMA)
    op.drop_index("ix_email_otps_user_id", table_name="email_otps", schema=SCHEMA)
    op.drop_table("email_otps", schema=SCHEMA)
    op.drop_index("ix_users_email", table_name="users", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
    # Enums retained for forward compatibility
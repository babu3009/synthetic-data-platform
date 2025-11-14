"""standardize enum bindings

Ensure enum types have expected lowercase values and no-op adjustments for
binding strategy changes (values_callable now used in ORM; DB enum labels
already lowercase so we only add any missing values safely).

Revision ID: 2025_11_14_120000
Revises: 2025_11_13_112500
Create Date: 2025-11-14 12:00:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2025_11_14_120000"
down_revision = "2025_11_13_112500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enum values if they do not already exist (Postgres 15 supports IF NOT EXISTS)
    # Email OTP purpose enum
    op.execute("ALTER TYPE emailotppurpose ADD VALUE IF NOT EXISTS 'email_verify';")
    op.execute("ALTER TYPE emailotppurpose ADD VALUE IF NOT EXISTS 'forgot_pwd';")
    op.execute("ALTER TYPE emailotppurpose ADD VALUE IF NOT EXISTS 'change_pwd';")

    # LLM provider kind enum
    op.execute("ALTER TYPE llm_provider_kind ADD VALUE IF NOT EXISTS 'openai';")
    op.execute("ALTER TYPE llm_provider_kind ADD VALUE IF NOT EXISTS 'anthropic';")
    op.execute("ALTER TYPE llm_provider_kind ADD VALUE IF NOT EXISTS 'ollama';")
    op.execute("ALTER TYPE llm_provider_kind ADD VALUE IF NOT EXISTS 'lmstudio';")
    op.execute("ALTER TYPE llm_provider_kind ADD VALUE IF NOT EXISTS 'custom';")

    # LLM task type enum
    op.execute("ALTER TYPE llm_task_type ADD VALUE IF NOT EXISTS 'chat';")
    op.execute("ALTER TYPE llm_task_type ADD VALUE IF NOT EXISTS 'embeddings';")
    op.execute("ALTER TYPE llm_task_type ADD VALUE IF NOT EXISTS 'tools';")

    # Project role enum (already uppercase in code; ensure labels exist)
    op.execute("ALTER TYPE projectrole ADD VALUE IF NOT EXISTS 'OWNER';")
    op.execute("ALTER TYPE projectrole ADD VALUE IF NOT EXISTS 'EDITOR';")
    op.execute("ALTER TYPE projectrole ADD VALUE IF NOT EXISTS 'VIEWER';")

    # User role enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'USER';")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ADMIN';")

    # User status enum
    op.execute("ALTER TYPE userstatus ADD VALUE IF NOT EXISTS 'PENDING_EMAIL_VERIFICATION';")
    op.execute("ALTER TYPE userstatus ADD VALUE IF NOT EXISTS 'PENDING_ADMIN_APPROVAL';")
    op.execute("ALTER TYPE userstatus ADD VALUE IF NOT EXISTS 'APPROVED';")
    op.execute("ALTER TYPE userstatus ADD VALUE IF NOT EXISTS 'REJECTED';")

    # Request / Artifact enums
    op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'relational';")
    op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'flat';")
    op.execute("ALTER TYPE requesttype ADD VALUE IF NOT EXISTS 'timeseries';")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'pending';")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'running';")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'completed';")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'failed';")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'cancelled';")
    op.execute("ALTER TYPE artifactformat ADD VALUE IF NOT EXISTS 'csv';")
    op.execute("ALTER TYPE artifactformat ADD VALUE IF NOT EXISTS 'xlsx';")
    op.execute("ALTER TYPE artifactformat ADD VALUE IF NOT EXISTS 'parquet';")
    op.execute("ALTER TYPE artifactformat ADD VALUE IF NOT EXISTS 'jsonl';")
    op.execute("ALTER TYPE artifactformat ADD VALUE IF NOT EXISTS 'html';")


def downgrade() -> None:
    # Downgrade is a no-op: removing enum values is not supported safely.
    pass
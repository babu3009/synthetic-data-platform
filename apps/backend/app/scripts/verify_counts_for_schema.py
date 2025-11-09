"""
Verify core and LLM table presence and row counts for the active schema.

Active schema is determined by app.db.base.SCHEMA_NAME which honors:
- USE_TESTING_SCHEMA=true -> TESTING_DB_SCHEMA
- else pytest override (TESTING_DB_SCHEMA if running tests)
- else DB_SCHEMA

Usage:
  python -m app.scripts.verify_counts_for_schema
"""
from __future__ import annotations

from typing import Sequence

from sqlalchemy import text

from app.core.config import settings
from app.db.base import SCHEMA_NAME as ACTIVE_SCHEMA
assert isinstance(ACTIVE_SCHEMA, str) and ACTIVE_SCHEMA, "ACTIVE_SCHEMA must be a non-empty string"
from app.db.session import sync_engine


def table_exists(schema: str, table: str) -> bool:
    with sync_engine.connect() as conn:
        res = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema AND table_name = :table
                """
            ),
            {"schema": schema, "table": table},
        )
        return res.scalar() is not None


def count_rows(schema: str, table: str) -> int:
    with sync_engine.connect() as conn:
        try:
            res = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{table}"))
            return int(res.scalar() or 0)
        except Exception:
            return -1


def main() -> None:
    print("--- Active DB configuration ---")
    print(f"DB_SCHEMA={settings.DB_SCHEMA}")
    print(f"TESTING_DB_SCHEMA={getattr(settings, 'TESTING_DB_SCHEMA', None)}")
    print(f"USE_TESTING_SCHEMA={getattr(settings, 'USE_TESTING_SCHEMA', None)}")
    print(f"ACTIVE_SCHEMA (from app.db.base)={ACTIVE_SCHEMA}")
    print()

    tables: Sequence[str] = (
        "projects",
        "llm_providers",
        "llm_credentials",
        "llm_models",
        "project_llm_settings",
    )

    print(f"--- Tables in schema '{ACTIVE_SCHEMA}' ---")
    for t in tables:
        exists = table_exists(ACTIVE_SCHEMA, t)
        count = count_rows(ACTIVE_SCHEMA, t) if exists else "n/a"
        print(f"{t:24} exists={str(exists):5} count={count}")


if __name__ == "__main__":
    main()

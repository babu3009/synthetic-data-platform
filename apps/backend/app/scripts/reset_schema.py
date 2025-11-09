"""
Drop and recreate the active metadata schema.

Active schema is resolved from app.db.base.SCHEMA_NAME, honoring USE_TESTING_SCHEMA.
"""
from sqlalchemy import text

from app.db.base import SCHEMA_NAME as ACTIVE_SCHEMA
from app.db.session import sync_engine


def main() -> None:
    assert isinstance(ACTIVE_SCHEMA, str) and ACTIVE_SCHEMA, "ACTIVE_SCHEMA must be a non-empty string"
    print(f"Resetting schema '{ACTIVE_SCHEMA}' (DROP CASCADE -> CREATE)...")
    with sync_engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text(f"DROP SCHEMA IF EXISTS {ACTIVE_SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {ACTIVE_SCHEMA}"))
    print("Schema reset complete.")


if __name__ == "__main__":
    main()

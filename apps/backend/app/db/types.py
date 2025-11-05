import json
from typing import Any, List, Optional

from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.dialects.postgresql import ARRAY


class StringArray(TypeDecorator):
    """
    Cross-dialect ARRAY(String) that stores as TEXT(JSON) on SQLite and as ARRAY(VARCHAR) on Postgres.

    - On Postgres: binds/returns Python lists normally via ARRAY(String).
    - On SQLite: serializes Python lists to JSON strings for storage in TEXT columns.
    """

    impl = ARRAY(String)
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        # Use TEXT on SQLite, ARRAY(VARCHAR) on Postgres
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String())
        return dialect.type_descriptor(ARRAY(String))

    def process_bind_param(self, value: Optional[List[str]], dialect) -> Any:  # type: ignore[override]
        if dialect.name == "sqlite":
            # Store list as JSON string
            return json.dumps(value or [])
        return value

    def process_result_value(self, value: Any, dialect) -> Optional[List[str]]:  # type: ignore[override]
        if dialect.name == "sqlite":
            if value is None:
                return []
            try:
                return json.loads(value)
            except Exception:
                return []
        return value

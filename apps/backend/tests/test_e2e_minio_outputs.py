from __future__ import annotations

import os
import uuid
import pytest
from pathlib import Path

from app.services.relational import generate_to_artifacts
from app.services.storage import get_storage, MinioStorage


@pytest.mark.e2e
def test_e2e_generate_and_upload_minio(tmp_path: Path):
    """
    Generate large relational data across three tables and upload CSV+Parquet to MinIO.

    Skips unless MINIO_ENDPOINT is configured and the MinIO client can be constructed.
    The row scale defaults to 100_000 per child table and 50_000 for parent to keep CI reasonable; set
    E2E_LARGE_ROWS=1 to use ~1M rows combined (e.g., 100k + 400k + 500k).
    """
    # Require MinIO configured
    try:
        store = get_storage()
        if not isinstance(store, MinioStorage):  # type: ignore
            pytest.skip("MinIO not configured/available; skipping E2E upload test")
    except Exception:
        pytest.skip("MinIO not configured/available; skipping E2E upload test")

    large = os.getenv("E2E_LARGE_ROWS", "0") == "1"
    # ~1M rows combined when large=True
    rows_parent = 100_000 if large else 50_000
    rows_child1 = 450_000 if large else 100_000
    rows_child2 = 450_000 if large else 100_000

    schema = {
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 1}},
                    {"name": "country", "provider": {"type": "categorical", "categories": ["US", "CA", "GB", "DE"]}},
                ],
            },
            {
                "name": "sessions",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 10_000}},
                    {"name": "user_id", "fk": {"to_table": "users", "to_column": "id"}},
                    {"name": "device", "provider": {"type": "categorical", "categories": ["mobile", "desktop", "tablet"]}},
                ],
            },
            {
                "name": "events",
                "columns": [
                    {"name": "id", "pk": True, "unique": True, "provider": {"type": "sequence", "start": 1_000_000}},
                    {"name": "session_id", "fk": {"to_table": "sessions", "to_column": "id"}},
                    {"name": "event_type", "provider": {"type": "categorical", "categories": ["view", "click", "purchase"]}},
                ],
            },
        ]
    }

    rows_per_table = {
        "users": rows_parent,
        "sessions": rows_child1,
        "events": rows_child2,
    }

    paths_by_table, _ = generate_to_artifacts(
        target_dir=tmp_path,
        schema=schema,
        rows_per_table=rows_per_table,
        formats=["csv", "parquet"],
        seed=42,
        chunk_size=50_000,
    )

    # Upload to MinIO under a unique prefix
    run_id = str(uuid.uuid4())
    storage = get_storage()
    for tname, fmap in paths_by_table.items():
        for fmt in ("csv", "parquet"):
            p = fmap.get(fmt)
            assert p and p.exists()
            object_name = f"e2e/{run_id}/{tname}.{fmt}"
            stored = storage.put_file(p, object_name)
            # Should be s3 URI and non-zero size
            assert stored.uri.startswith("s3://")
            assert stored.size > 0

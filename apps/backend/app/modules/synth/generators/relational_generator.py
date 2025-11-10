"""Module-level relational generation adapter (Phase 3).

Thin wrapper over legacy `app.services.relational.generate_to_artifacts`.
Future responsibilities: adaptive chunk sizing, pre-flight validation,
progress callbacks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services import relational as legacy_relational


def generate(
    *,
    target_dir: Path,
    schema: Dict[str, Any],
    rows_per_table: Dict[str, int],
    formats: List[str],
    seed: int = 0,
    chunk_size: int = 50_000,
    unique_retry_cap: int = 5,
    db_writeback: Optional[Dict[str, Any]] = None,
    kafka_publish: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Path]], Dict[str, Any]]:
    return legacy_relational.generate_to_artifacts(
        target_dir=target_dir,
        schema=schema,
        rows_per_table=rows_per_table,
        formats=formats,
        seed=seed,
        chunk_size=chunk_size,
        unique_retry_cap=unique_retry_cap,
        db_writeback=db_writeback,
        kafka_publish=kafka_publish,
    )

__all__ = ["generate"]

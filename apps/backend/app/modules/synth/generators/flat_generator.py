"""Module-level flat generation adapter (Phase 3).

Wraps the legacy `app.services.flat` generation functions to allow future
enhancements (caching, tracing, metrics) without changing callers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from app.services import flat as legacy_flat


def preview(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate a small preview of flat rows.

    Delegates to the legacy implementation; kept thin for now.
    """
    return legacy_flat.preview(schema)


def generate(
    *,
    target_dir: Path,
    schema: Dict[str, Any],
    total_rows: int,
    formats: List[str],
    chunk_size: int = 50_000,
    db_writeback: Optional[Dict[str, Any]] = None,
    kafka_publish: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Path], Dict[str, Any]]:
    """Generate flat data artifacts.

    Returns the list of artifact paths and column statistics.
    """
    return legacy_flat.generate_to_artifacts(
        target_dir=target_dir,
        schema=schema,
        total_rows=total_rows,
        formats=formats,
        chunk_size=chunk_size,
        db_writeback=db_writeback,
        kafka_publish=kafka_publish,
    )

__all__ = ["preview", "generate"]

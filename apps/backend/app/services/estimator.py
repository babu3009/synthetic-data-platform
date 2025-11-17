from __future__ import annotations

from typing import Any, Dict, List, Tuple


# Rough bytes-per-value for simple types (fallback for unknowns)
_TYPE_SIZE = {
    "int": 8,
    "bigint": 8,
    "smallint": 2,
    "float": 8,
    "double": 8,
    "numeric": 16,
    "bool": 1,
    "boolean": 1,
    "date": 4,
    "timestamp": 8,
    "text": 32,
    "varchar": 32,
    "string": 32,
}


_PROVIDER_COMPLEXITY = {
    # cheap
    "sequence": 1.0,
    "constant": 0.5,
    "uniform": 1.0,
    "categorical": 1.2,
    "pattern": 1.5,
    # medium
    "faker": 3.0,
    "distribution": 2.0,
    # fk sampling
    "fk": 0.8,
}


def _col_size_bytes(col: Dict[str, Any]) -> int:
    dtype = (col.get("dtype") or col.get("type") or "string").lower()
    for k, v in _TYPE_SIZE.items():
        if k in dtype:
            return v
    # default average size
    return 32


def _provider_complexity(col: Dict[str, Any]) -> float:
    if col.get("fk"):
        return _PROVIDER_COMPLEXITY["fk"]
    prov = col.get("provider") or {}
    # Handle both dict and string provider formats
    if isinstance(prov, str):
        ptype = prov.lower()
    elif isinstance(prov, dict):
        ptype = (prov.get("type") or "").lower()
    else:
        ptype = ""
    return _PROVIDER_COMPLEXITY.get(ptype, 1.0)


def estimate_relational(schema: Dict[str, Any], rows_per_table: Dict[str, int]) -> Dict[str, Any]:
    import logging
    logger = logging.getLogger(__name__)
    
    tables: List[Dict[str, Any]] = schema.get("tables", [])
    logger.info(f"Estimating for {len(tables)} tables, rows_per_table={rows_per_table}")
    
    per_table: Dict[str, Any] = {}
    total_rows = 0
    total_bytes_csv = 0
    total_bytes_parquet = 0
    total_complexity = 0.0
    for t in tables:
        tname_any = t.get("name")
        if not isinstance(tname_any, str):
            # skip unnamed tables
            continue
        tname = tname_any
        
        # Try multiple sources for row count:
        # 1. rows_per_table dict (passed separately)
        # 2. table's "rows" field (direct number)
        # 3. table's "rowTarget" field (frontend format: {type: 'absolute', value: N})
        n = rows_per_table.get(tname)
        if n is None:
            n = t.get("rows")
        if n is None:
            row_target = t.get("rowTarget")
            if isinstance(row_target, dict) and row_target.get("type") == "absolute":
                n = row_target.get("value")
        
        # Convert to int, default to 0
        n = int(n or 0)
        logger.info(f"Table '{tname}': final row count={n}")
        
        cols = t.get("columns", [])
        row_size = sum(_col_size_bytes(c) for c in cols) + max(0, len(cols) - 1)  # commas in CSV
        # Header cost once per table for CSV is negligible at scale
        complexity = sum(_provider_complexity(c) for c in cols) or 1.0
        per_table[tname] = {
            "rows": n,
            "row_size_bytes_est": row_size,
            "table_csv_bytes_est": n * row_size,
            "complexity": complexity,
        }
        total_rows += n
        total_bytes_csv += n * row_size
        total_bytes_parquet += int(n * row_size * 0.3)  # rough parquet compression factor
        total_complexity += complexity * max(n, 1)

    # throughput (rows/sec) baseline for complexity=1 on modest hardware
    base_rps = 200_000.0
    # scale by average complexity per row
    avg_complexity = (total_complexity / max(total_rows, 1)) if total_rows else 1.0
    est_rows_per_sec = max(5_000.0, base_rps / max(avg_complexity, 0.25))
    est_seconds = total_rows / est_rows_per_sec if total_rows else 0.0

    return {
        "rows": total_rows,  # Frontend expects 'rows'
        "size_bytes": total_bytes_csv,  # Frontend expects 'size_bytes'
        "seconds": est_seconds,  # Frontend expects 'seconds'
        "total_rows": total_rows,  # Keep for backward compatibility
        "bytes_csv_est": total_bytes_csv,
        "bytes_parquet_est": total_bytes_parquet,
        "rows_per_sec_est": est_rows_per_sec,
        "seconds_est": est_seconds,
        "per_table": per_table,
    }

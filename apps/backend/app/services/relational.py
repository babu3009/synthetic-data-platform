from __future__ import annotations

from collections import defaultdict, Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from synth.providers.registry import ProviderRegistry
from app.services.writers import CSVWriter, ParquetWriter, PostgresUpsertWriter, KafkaEventWriter
from openpyxl import Workbook


@dataclass
class FKRef:
    column: str
    to_table: str
    to_column: str
    nullable: bool = False
    sampling: str = "uniform"  # or "weighted"


def topo_sort(tables: List[Dict[str, Any]]) -> List[str]:
    nodes = [t["name"] for t in tables]
    indeg: Dict[str, int] = {n: 0 for n in nodes}
    adj: Dict[str, List[str]] = {n: [] for n in nodes}

    for t in tables:
        child = t["name"]
        for c in t.get("columns", []):
            fk = c.get("fk")
            if fk:
                parent = fk["to_table"]
                if parent in adj:
                    adj[parent].append(child)
                    indeg[child] += 1

    q = deque([n for n in nodes if indeg[n] == 0])
    order: List[str] = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(nodes):
        # cycle; fallback to input order
        return nodes
    return order


def _build_generators(table: Dict[str, Any], seed: int) -> List[Tuple[str, Any]]:
    gens: List[Tuple[str, Any]] = []
    for col in table.get("columns", []):
        name = col["name"]
        provider_cfg = col.get("provider") or {"type": "sequence"}
        if col.get("unique"):
            provider_cfg = {**provider_cfg, "unique": True}
        gen = ProviderRegistry.from_config(provider_cfg)
        gens.append((name, gen))
    return gens


def _build_fk_defs(table: Dict[str, Any]) -> List[FKRef]:
    fks: List[FKRef] = []
    for col in table.get("columns", []):
        fk = col.get("fk")
        if fk:
            fks.append(
                FKRef(
                    column=col["name"],
                    to_table=fk["to_table"],
                    to_column=fk.get("to_column", fk.get("to_col", "id")),
                    nullable=bool(col.get("nullable", False)),
                    sampling=fk.get("sampling", "uniform"),
                )
            )
    return fks


def _sample_parent_key(parent_pool: List[Any], degrees: Counter, mode: str) -> Any:
    if not parent_pool:
        return None
    if mode == "weighted":
        # Weighted by current degree -> prefer less used parents (inverse weighting)
        # Compute weights as 1/(1+degree)
        weights = [1.0 / (1 + degrees.get(k, 0)) for k in parent_pool]
        # simple roulette wheel selection with deterministic-ish fallback: pick min degree
        min_deg = min(degrees.get(k, 0) for k in parent_pool)
        # choose the first key with min degree to keep deterministic ordering for tests
        for k in parent_pool:
            if degrees.get(k, 0) == min_deg:
                degrees[k] += 1
                return k
    # uniform: round-robin using degrees to rotate fairly
    min_deg = min(degrees.get(k, 0) for k in parent_pool)
    for k in parent_pool:
        if degrees.get(k, 0) == min_deg:
            degrees[k] += 1
            return k
    return parent_pool[0]


def generate_to_artifacts(
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
    """
    Generate relational data according to the provided schema and write artifacts.

    Returns (paths_by_table, report) where paths_by_table maps table->format->Path and
    report contains fk_coverage and collision rates.
    """
    tables: List[Dict[str, Any]] = schema["tables"]
    order = topo_sort(tables)
    table_map = {t["name"]: t for t in tables}

    # Writers per table
    paths_by_table: Dict[str, Dict[str, Path]] = defaultdict(dict)
    csv_writers: Dict[str, CSVWriter] = {}
    parquet_writers: Dict[str, ParquetWriter] = {}
    db_writers: Dict[str, PostgresUpsertWriter] = {}
    kafka_writer: Optional[KafkaEventWriter] = None

    # Multi-sheet XLSX
    wb = Workbook(write_only=True)
    sheet_map = {}

    # PK pools and degrees for FK sampling
    pk_pools: Dict[str, List[Any]] = defaultdict(list)
    degrees: Dict[str, Counter] = defaultdict(Counter)  # by parent table -> key->count

    # Track uniqueness collisions
    collisions: Dict[Tuple[str, str], int] = Counter()
    seen_unique: Dict[Tuple[str, str], set] = defaultdict(set)  # (table,col) -> set

    # FK coverage
    fk_valid_counts: Dict[Tuple[str, str], int] = Counter()  # (table,col) -> valid refs

    # Prepare writers
    target_dir.mkdir(parents=True, exist_ok=True)

    for tname in order:
        table = table_map[tname]
        columns = [c["name"] for c in table.get("columns", [])]
        # per table writers for csv/parquet
        if "csv" in formats:
            csv_writers[tname] = CSVWriter(target_dir / f"{tname}.csv", columns)
            paths_by_table[tname]["csv"] = target_dir / f"{tname}.csv"
        if "parquet" in formats:
            parquet_writers[tname] = ParquetWriter(target_dir / f"{tname}.parquet", columns)
            paths_by_table[tname]["parquet"] = target_dir / f"{tname}.parquet"
        # optional DB upsert per table
        if db_writeback and db_writeback.get("enabled"):
            dsn = db_writeback.get("dsn")
            base_table = db_writeback.get("table_prefix", "") + tname
            full_table = db_writeback.get("table", None) or db_writeback.get("table_map", {}).get(tname, base_table)
            conflict_cols = db_writeback.get("conflict_columns_map", {}).get(tname) or [c["name"] for c in table.get("columns", []) if c.get("pk")]
            if dsn and full_table and conflict_cols:
                db_writers[tname] = PostgresUpsertWriter(
                    dsn=dsn,
                    table=full_table,
                    columns=columns,
                    conflict_columns=conflict_cols,
                    update_columns=[c for c in columns if c not in conflict_cols],
                    batch_size=int(db_writeback.get("batch_size", 10_000)),
                )
        # xlsx sheet
        sheet_map[tname] = wb.create_sheet(tname[:31])  # Excel sheet name max 31 chars
        sheet_map[tname].append(columns)

    # optional Kafka writer once (topic may include table name via prefix if provided later)
    if kafka_publish and kafka_publish.get("enabled"):
        brokers = kafka_publish.get("brokers")
        topic = kafka_publish.get("topic")
        key_field = kafka_publish.get("key_field")
        headers = kafka_publish.get("headers") or {}
        if brokers and topic:
            kafka_writer = KafkaEventWriter(
                brokers=brokers,
                topic=topic,
                key_field=key_field,
                extra_headers=headers,
                linger_ms=int(kafka_publish.get("linger_ms", 20)),
                batch_size=int(kafka_publish.get("batch_size", 32768)),
                acks=kafka_publish.get("acks", "all"),
            )

    # Generation
    for tname in order:
        table = table_map[tname]
        # Determine number of rows robustly (guard against None)
        n_raw = rows_per_table.get(tname)
        if n_raw is None:
            n_raw = table.get("rows", 0) or 0
        n = int(n_raw)
        if n <= 0:
            continue
        gens = _build_generators(table, seed)
        null_probs = {c["name"]: c.get("null_prob", 0.0) for c in table.get("columns", [])}
        # Identify PK columns (assume single-column pk for simplicity)
        pk_cols = [c["name"] for c in table.get("columns", []) if c.get("pk")]
        pk_col = pk_cols[0] if pk_cols else None
        # FK defs
        fk_defs = _build_fk_defs(table)

        # Maintain continuous sequence values across chunks per column when provider is sequence
        seq_state: Dict[str, Dict[str, Any]] = {}
        for cdef in table.get("columns", []):
            pc = cdef.get("provider") or {}
            if pc.get("type") == "sequence":
                start = int(pc.get("start", 0))
                step = int(pc.get("step", 1))
                template = pc.get("template")
                seq_state[cdef["name"]] = {"next": start, "step": step, "template": template}

        buf: List[Dict[str, Any]] = []
        remaining = n
        while remaining > 0:
            take = min(remaining, chunk_size)
            # Column-wise generation
            cols: Dict[str, List[Any]] = {}
            for col_name, gen in gens:
                values = gen(take, {"global_seed": seed, "table": tname, "column": col_name})
                p = null_probs.get(col_name, 0.0)
                if p > 0:
                    step = max(1, int(1 / p))
                    for i in range(0, take, step):
                        values[i] = None
                cols[col_name] = values

            # Apply FK sampling to override FK columns
            for fk in fk_defs:
                parent_keys = pk_pools.get(fk.to_table, [])
                deg = degrees[fk.to_table]
                vals: List[Any] = []
                for i in range(take):
                    if not parent_keys:
                        # no parent generated yet -> None or raise
                        vals.append(None if fk.nullable else None)
                    else:
                        k = _sample_parent_key(parent_keys, deg, fk.sampling)
                        vals.append(k)
                        if k is not None:
                            fk_valid_counts[(tname, fk.column)] += 1
                cols[fk.column] = vals

            # Override sequence columns to ensure continuity across chunks
            for col_name, st in seq_state.items():
                vals: List[Any] = []
                cur = st["next"]
                step = st["step"]
                template = st.get("template")
                for _ in range(take):
                    v = cur if template is None else (template.format(i=(cur - st["next"]) // step, value=cur))
                    vals.append(v)
                    cur += step
                st["next"] = cur
                cols[col_name] = vals

            # Apply uniqueness with capped retries
            for cdef in table.get("columns", []):
                if not cdef.get("unique"):
                    continue
                key = (tname, cdef["name"])
                uniq = seen_unique[key]
                vals = cols[cdef["name"]]
                for i, v in enumerate(vals):
                    if v is None:
                        continue
                    attempts = 0
                    while v in uniq and attempts < unique_retry_cap:
                        attempts += 1
                        # sample one more value from the generator deterministically by shifting seed context
                        v = ProviderRegistry.from_config(cdef.get("provider", {"type": "sequence"}))(1, {"global_seed": seed + attempts, "table": tname, "column": cdef["name"]})[0]
                    if v in uniq:
                        collisions[key] += 1
                    else:
                        uniq.add(v)
                    vals[i] = v
                cols[cdef["name"]] = vals

            # Build rows and track pk pool
            for i in range(take):
                row = {name: cols[name][i] for name, _ in gens}
                buf.append(row)
                if pk_col:
                    pk_val = row.get(pk_col)
                    if pk_val is not None:
                        pk_pools[tname].append(pk_val)

            # Flush chunk
            if buf:
                if tname in csv_writers:
                    csv_writers[tname].write_rows(buf)
                if tname in parquet_writers:
                    parquet_writers[tname].write_rows(buf)
                if tname in db_writers:
                    db_writers[tname].write_rows(buf)
                if kafka_writer is not None:
                    # Allow optional table name in payload
                    if kafka_publish and kafka_publish.get("include_table_name"):
                        out_buf = [dict(r, __table__=tname) for r in buf]
                        kafka_writer.write_rows(out_buf)
                    else:
                        kafka_writer.write_rows(buf)
                # xlsx
                ws = sheet_map[tname]
                for r in buf:
                    ws.append([r.get(c["name"]) for c in table.get("columns", [])])
                buf.clear()
            remaining -= take

    # Close writers
    for w in csv_writers.values():
        w.close()
    for w in parquet_writers.values():
        w.close()
    for w in db_writers.values():
        w.close()
    if kafka_writer is not None:
        kafka_writer.close()

    xlsx_path = target_dir / "data.xlsx"
    wb.save(xlsx_path)

    # add xlsx path to all tables (single workbook path)
    for tname in order:
        paths_by_table[tname]["xlsx"] = xlsx_path

    # Build report
    report: Dict[str, Any] = {
        "fk_coverage": {},
        "collisions": {},
    }
    for tname in order:
        table = table_map[tname]
        n = int((rows_per_table.get(tname) if rows_per_table.get(tname) is not None else table.get("rows", 0)) or 0)
        for fk in _build_fk_defs(table):
            valid = fk_valid_counts.get((tname, fk.column), 0)
            report["fk_coverage"][f"{tname}.{fk.column}"] = {
                "valid_pct": (valid / n) if n else 0.0,
                "orphans": n - valid,
            }
        for cdef in table.get("columns", []):
            if cdef.get("unique"):
                key = (tname, cdef["name"])
                report["collisions"][f"{tname}.{cdef['name']}"] = collisions.get(key, 0)

    return paths_by_table, report

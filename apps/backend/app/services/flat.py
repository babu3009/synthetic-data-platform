from __future__ import annotations

"""DEPRECATED (Phase 5): legacy flat data generation implementation.

This module remains for backward compatibility. New code should import
`preview` and `generate_to_artifacts` via:

    from app.modules.synth.generators.flat_generator import preview, generate_to_artifacts

The logic will eventually be relocated fully under `app/modules/synth/`.
"""

from collections import Counter
from dataclasses import dataclass, field
from math import isnan
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from app.core.config import settings
from synth.providers.registry import ProviderRegistry
from .writers import get_writer, KafkaEventWriter, PostgresUpsertWriter


@dataclass
class ColumnStats:
    count: int = 0
    nulls: int = 0
    mean: float = 0.0
    m2: float = 0.0  # sum of squares of differences from the current mean
    min: Optional[float] = None
    max: Optional[float] = None
    cardinality: set[Any] = field(default_factory=set)  # track unique values up to a threshold
    topk_counter: Counter[Any] = field(default_factory=Counter)

    def __post_init__(self):
        # Fields already initialized via default_factory; keep method for future extensions
        pass
    def add(self, v: Any):
        self.count += 1
        if v is None:
            self.nulls += 1
            return
        # numeric stats if possible
        num: Optional[float] = None
        if isinstance(v, (int, float)) and not (isinstance(v, float) and isnan(v)):
            num = float(v)
        # min/max
        try:
            if self.min is None or (num is not None and num < self.min):
                self.min = num if num is not None else self.min
            if self.max is None or (num is not None and num > self.max):
                self.max = num if num is not None else self.max
        except Exception:
            pass
        if num is not None:
            # Welford's algorithm
            delta = num - self.mean
            self.mean += delta / self.count
            delta2 = num - self.mean
            self.m2 += delta2 * delta
        # cardinality (bounded)
        if len(self.cardinality) < 100_000:
            try:
                self.cardinality.add(v)
            except Exception:
                pass
        # topk
        try:
            self.topk_counter[v] += 1
        except Exception:
            pass

    def to_dict(self) -> Dict[str, Any]:
        stdev = (self.m2 / (self.count - 1)) ** 0.5 if self.count > 1 else 0.0
        null_pct = self.nulls / self.count if self.count else 0.0
        topk = [
            {"value": k, "count": c}
            for k, c in self.topk_counter.most_common(10)
        ]
        return {
            "min": self.min,
            "max": self.max,
            "mean": self.mean,
            "stdev": stdev,
            "cardinality": len(self.cardinality),
            "null_pct": null_pct,
            "topk": topk,
        }


def build_generators(fields: List[Dict[str, Any]], seed: int) -> List[Tuple[str, Any]]:
    gens: List[Tuple[str, Any]] = []
    for f in fields:
        name = f["name"]
        provider_cfg = f["provider"]
        # merge unique/nullability into provider config if present
        if f.get("unique"):
            provider_cfg = {**provider_cfg, "unique": True}
        gen = ProviderRegistry.from_config(provider_cfg)
        gens.append((name, gen))
    return gens


def row_iter(gens: List[Tuple[str, Any]], n: int, seed: int, null_probs: Dict[str, float]) -> Iterator[Dict[str, Any]]:
    # generate in column-wise batches for performance
    context_template = {"global_seed": seed, "table": "flat"}
    # we compute per-column arrays chunk-wise to avoid full memory
    chunk = 10_000
    remaining = n
    i0 = 0
    while remaining > 0:
        take = min(chunk, remaining)
        cols: Dict[str, List[Any]] = {}
        for name, gen in gens:
            ctx = {**context_template, "column": name}
            values = gen(take, ctx)
            p_null = null_probs.get(name, 0.0)
            if p_null > 0:
                # apply nulls deterministically: every int(1/p) value
                if p_null >= 1:
                    values = [None] * take
                else:
                    step = max(1, int(1 / p_null))
                    for j in range(0, take, step):
                        values[j] = None
            cols[name] = values
        for j in range(take):
            yield {name: cols[name][j] for name, _ in gens}
        remaining -= take
        i0 += take


def preview(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = schema["fields"]
    seed = schema.get("seed", 0)
    gens = build_generators(fields, seed)
    null_probs = {f["name"]: f.get("null_prob", 0.0) for f in fields}
    return [next_row for _, next_row in zip(range(100), row_iter(gens, 100, seed, null_probs))]


def generate_to_artifacts(
    *,
    target_dir: Path,
    schema: Dict[str, Any],
    total_rows: int,
    formats: List[str],
    chunk_size: int = 50_000,
    db_writeback: Optional[Dict[str, Any]] = None,
    kafka_publish: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Path], Dict[str, Any]]:
    fields = schema["fields"]
    seed = schema.get("seed", 0)
    gens = build_generators(fields, seed)
    null_probs = {f["name"]: f.get("null_prob", 0.0) for f in fields}
    fieldnames = [f["name"] for f in fields]

    writers = {}
    for fmt in formats:
        ext = "csv" if fmt == "csv" else ("jsonl" if fmt == "jsonl" else ("parquet" if fmt == "parquet" else "xlsx"))
        writers[fmt] = get_writer(fmt, target_dir / f"data.{ext}", fieldnames)

    # optional DB and Kafka writers
    db_writer: Optional[PostgresUpsertWriter] = None
    if db_writeback and db_writeback.get("enabled"):
        dsn = db_writeback.get("dsn")
        table = db_writeback.get("table") or schema.get("name", "flat_data")
        conflict_cols = db_writeback.get("conflict_columns") or []
        if dsn and table:
            db_writer = PostgresUpsertWriter(
                dsn=dsn,
                table=table,
                columns=fieldnames,
                conflict_columns=conflict_cols,
                update_columns=[c for c in fieldnames if c not in conflict_cols],
                batch_size=int(db_writeback.get("batch_size", 10_000)),
            )
    kafka_writer: Optional[KafkaEventWriter] = None
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

    # stats per column
    stats = {name: ColumnStats() for name in fieldnames}

    written = 0
    buf: List[Dict[str, Any]] = []
    for r in row_iter(gens, total_rows, seed, null_probs):
        buf.append(r)
        for k, v in r.items():
            stats[k].add(v)
        if len(buf) >= chunk_size:
            for w in writers.values():
                w.write_rows(buf)
            if db_writer is not None:
                db_writer.write_rows(buf)
            if kafka_writer is not None:
                kafka_writer.write_rows(buf)
            written += len(buf)
            buf.clear()

    if buf:
        for w in writers.values():
            w.write_rows(buf)
        if db_writer is not None:
            db_writer.write_rows(buf)
        if kafka_writer is not None:
            kafka_writer.write_rows(buf)
        written += len(buf)
        buf.clear()

    output_paths: List[Path] = []
    for fmt, w in writers.items():
        w.close()
        output_paths.append(target_dir / w.path.name)
    if db_writer is not None:
        db_writer.close()
    if kafka_writer is not None:
        kafka_writer.close()

    stat_dict = {k: s.to_dict() for k, s in stats.items()}
    return output_paths, stat_dict

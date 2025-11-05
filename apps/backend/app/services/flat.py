from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isnan
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from app.core.config import settings
from synth.providers.registry import ProviderRegistry
from .writers import get_writer


@dataclass
class ColumnStats:
    count: int = 0
    nulls: int = 0
    mean: float = 0.0
    m2: float = 0.0  # sum of squares of differences from the current mean
    min: Optional[float] = None
    max: Optional[float] = None
    cardinality: set = None  # track unique values up to a threshold
    topk_counter: Counter = None

    def __post_init__(self):
        self.cardinality = set()
        self.topk_counter = Counter()

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
            written += len(buf)
            buf.clear()

    if buf:
        for w in writers.values():
            w.write_rows(buf)
        written += len(buf)
        buf.clear()

    output_paths: List[Path] = []
    for fmt, w in writers.items():
        w.close()
        output_paths.append(target_dir / w.path.name)

    stat_dict = {k: s.to_dict() for k, s in stats.items()}
    return output_paths, stat_dict

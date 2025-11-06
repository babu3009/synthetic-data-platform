from __future__ import annotations

import csv
import json
from typing import Any, Dict, Iterable, List, Optional

from pathlib import Path

# Parquet
import pyarrow as pa
import pyarrow.parquet as pq

# XLSX
from openpyxl import Workbook

# Optional Kafka
try:  # pragma: no cover - optional dependency
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

# Optional SQLAlchemy for DB upsert
from sqlalchemy import create_engine, text  # type: ignore
from sqlalchemy.engine import Engine, Connection


class BaseWriter:
    def write_rows(self, rows: Iterable[Dict]):
        raise NotImplementedError

    def close(self) -> int:
        """Return total bytes written if available."""
        return 0


class CSVWriter(BaseWriter):
    def __init__(self, path: Path, fieldnames: List[str]):
        self.path = path
        self.file = path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=fieldnames)
        self.writer.writeheader()

    def write_rows(self, rows: Iterable[Dict]):
        for r in rows:
            self.writer.writerow(r)

    def close(self) -> int:
        self.file.flush()
        self.file.close()
        return self.path.stat().st_size


class JSONLWriter(BaseWriter):
    def __init__(self, path: Path):
        self.path = path
        self.file = path.open("w", encoding="utf-8")

    def write_rows(self, rows: Iterable[Dict]):
        for r in rows:
            self.file.write(json.dumps(r, ensure_ascii=False) + "\n")

    def close(self) -> int:
        self.file.flush()
        self.file.close()
        return self.path.stat().st_size


class ParquetWriter(BaseWriter):
    def __init__(self, path: Path, fieldnames: List[str]):
        self.path = path
        self.fieldnames = fieldnames
        self._writer: Optional[pq.ParquetWriter] = None

    def write_rows(self, rows: Iterable[Dict]):
        batch = [ {k: r.get(k) for k in self.fieldnames} for r in rows ]
        if not batch:
            return
        table = pa.Table.from_pylist(batch)
        if self._writer is None:
            self._writer = pq.ParquetWriter(self.path, table.schema)
        self._writer.write_table(table)

    def close(self) -> int:
        if self._writer is not None:
            self._writer.close()
        return self.path.stat().st_size if self.path.exists() else 0


class XLSXWriter(BaseWriter):
    def __init__(self, path: Path, fieldnames: List[str]):
        self.path = path
        self.wb = Workbook(write_only=True)
        self.ws = self.wb.create_sheet("data")
        # header
        self.ws.append(fieldnames)

    def write_rows(self, rows: Iterable[Dict]):
        for r in rows:
            self.ws.append(list(r.values()))

    def close(self) -> int:
        # remove default sheet if present
        if "Sheet" in self.wb.sheetnames and len(self.wb.sheetnames) > 1:
            std = self.wb["Sheet"]
            self.wb.remove(std)
        self.wb.save(self.path)
        return self.path.stat().st_size


def get_writer(fmt: str, path: Path, fieldnames: List[str]) -> BaseWriter:
    fmt = fmt.lower()
    if fmt == "csv":
        return CSVWriter(path, fieldnames)
    if fmt == "jsonl":
        return JSONLWriter(path)
    if fmt == "parquet":
        return ParquetWriter(path, fieldnames)
    if fmt == "xlsx":
        return XLSXWriter(path, fieldnames)
    raise ValueError(f"Unsupported format: {fmt}")


class KafkaEventWriter(BaseWriter):
    """
    Publish rows to Kafka as JSON events.

    Config:
    - brokers: List[str] or comma-separated string
    - topic: str
    - key_field: Optional[str] used for partitioning
    - extra_headers: Optional[Dict[str,str]] to include as record headers
    - linger_ms, batch_size, acks: Optional producer tuning
    """

    def __init__(
        self,
        *,
        brokers: List[str] | str,
        topic: str,
        key_field: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        linger_ms: int = 20,
        batch_size: int = 32768,
        acks: str | int = "all",
    ) -> None:
        if KafkaProducer is None:
            raise RuntimeError("kafka-python is not installed. Add kafka-python to requirements.")
        if isinstance(brokers, str):
            brokers = [b.strip() for b in brokers.split(",") if b.strip()]
        self.topic = topic
        self.key_field = key_field
        self.extra_headers = extra_headers or {}
        # Create producer
        self.producer = KafkaProducer(
            bootstrap_servers=brokers,
            acks=acks,
            linger_ms=linger_ms,
            batch_size=batch_size,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: (str(k).encode("utf-8") if k is not None else None),
        )

    def write_rows(self, rows: Iterable[Dict]):
        headers = [(k, v.encode("utf-8")) for k, v in self.extra_headers.items()]
        for r in rows:
            key = r.get(self.key_field) if self.key_field else None
            self.producer.send(self.topic, key=key, value=r, headers=headers)

    def close(self) -> int:
        try:
            self.producer.flush()
            self.producer.close()
        except Exception:
            pass
        return 0


class PostgresUpsertWriter(BaseWriter):
    """
    Batched UPSERT into a Postgres table using a single transaction.

    Required config:
    - dsn: PostgreSQL DSN string, e.g. postgresql+psycopg2://user:pass@host:5432/db
    - table: target table name (optionally schema-qualified: schema.table)
    - conflict_columns: list of columns to use for ON CONFLICT

    Optional config:
    - batch_size: number of rows per INSERT VALUES batch (default 10_000)
    - update_columns: list of columns to update on conflict (defaults to all except conflict columns)
    """

    def __init__(
        self,
        *,
        dsn: str,
        table: str,
        columns: List[str],
        conflict_columns: List[str],
        update_columns: Optional[List[str]] = None,
        batch_size: int = 10_000,
        autocommit: bool = False,
    ) -> None:
        self.engine: Engine = create_engine(dsn, future=True)
        self.table = table
        self.columns = columns
        self.conflict = conflict_columns
        self.update_columns = update_columns or [c for c in columns if c not in conflict_columns]
        self.batch_size = batch_size
        self._conn: Optional[Connection] = None
        self._trans = None
        self._buffer: List[Dict[str, Any]] = []
        self._bytes = 0
        self._autocommit = autocommit

    def _ensure_conn(self):
        if self._conn is None:
            self._conn = self.engine.connect()
            if not self._autocommit:
                self._trans = self._conn.begin()

    def _flush(self):
        if not self._buffer:
            return
        self._ensure_conn()
        rows = self._buffer
        self._buffer = []
        # Build INSERT ... ON CONFLICT ... DO UPDATE
        cols = self.columns
        placeholders = []
        params: Dict[str, Any] = {}
        for i, row in enumerate(rows):
            vals = []
            for c in cols:
                key = f"{c}_{i}"
                vals.append(f":{key}")
                params[key] = row.get(c)
            placeholders.append(f"({', '.join(vals)})")
        cols_sql = ", ".join([f'"{c}"' for c in cols])
        values_sql = ", ".join(placeholders)
        conflict_sql = ", ".join([f'"{c}"' for c in self.conflict])
        update_sql = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in self.update_columns])
        stmt = text(
            f"INSERT INTO {self.table} ({cols_sql}) VALUES {values_sql} "
            f"ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql}"
        )
        assert self._conn is not None
        self._conn.execute(stmt, params)
        # Approximate bytes: sum of JSON length of rows
        try:
            self._bytes += sum(len(json.dumps(r, ensure_ascii=False)) for r in rows)
        except Exception:
            pass

    def write_rows(self, rows: Iterable[Dict]):
        for r in rows:
            self._buffer.append(r)
            if len(self._buffer) >= self.batch_size:
                self._flush()

    def close(self) -> int:
        try:
            self._flush()
            if self._trans is not None:
                self._trans.commit()
        except Exception:
            if self._trans is not None:
                try:
                    self._trans.rollback()
                except Exception:
                    pass
            raise
        finally:
            try:
                if self._conn is not None:
                    self._conn.close()
            finally:
                if self.engine is not None:
                    self.engine.dispose()
        return self._bytes

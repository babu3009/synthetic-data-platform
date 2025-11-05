from __future__ import annotations

import csv
import json
from typing import Dict, Iterable, List, Optional

from pathlib import Path

# Parquet
import pyarrow as pa
import pyarrow.parquet as pq

# XLSX
from openpyxl import Workbook


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

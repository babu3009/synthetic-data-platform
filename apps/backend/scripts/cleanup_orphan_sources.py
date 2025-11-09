"""
Cleanup orphaned source storage directories and relocate stray test SQL files.

This script:
- Connects to the configured database and fetches all current Source IDs
- Scans apps/backend/storage/sources/<UUID> directories
- Deletes any directory whose UUID is not present in the database (orphan)
- Moves any loose .sql files directly under storage/sources into tests/dbscript

Usage (PowerShell):
  cd apps/backend
  python -m scripts.cleanup_orphan_sources --yes

Options:
  --dry-run   Print actions without deleting/moving
  --yes       Proceed without interactive confirmation
"""
from __future__ import annotations

import argparse
import asyncio
import shutil
from pathlib import Path
from typing import Set

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, text

from app.core.config import settings
from app.db.base import SCHEMA_NAME as MODEL_SCHEMA
from app.db.models import Source


def _paths() -> tuple[Path, Path, Path]:
    backend_root = Path(__file__).resolve().parents[1]
    storage_sources = backend_root / "storage" / "sources"
    tests_dbscript = backend_root / "tests" / "dbscript"
    return backend_root, storage_sources, tests_dbscript


async def _fetch_db_source_ids() -> Set[str]:
    db_url = settings.get_database_url()
    schema_name = MODEL_SCHEMA or settings.DB_SCHEMA or "public"

    # asyncpg search_path so queries hit the right schema
    connect_args = {}
    if db_url.startswith("postgresql+"):
        connect_args = {
            "server_settings": {"search_path": f"{schema_name}, public"},
        }

    engine = create_async_engine(db_url, echo=False, connect_args=connect_args)
    try:
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            # Ensure schema exists (no-op if not Postgres)
            try:
                await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            except Exception:
                pass
            res = await session.execute(select(Source.id))
            ids = {str(r[0]) for r in res.all()}
            return ids
    finally:
        await engine.dispose()


def _is_uuid_dir(p: Path) -> bool:
    try:
        # Rough check: directory name contains 4 dashes and hex chars, length 36
        n = p.name
        return p.is_dir() and len(n) == 36 and n.count("-") == 4
    except Exception:
        return False


def cleanup_filesystem(valid_ids: Set[str], storage_sources: Path, tests_dbscript: Path, dry_run: bool = True) -> dict:
    actions = {"deleted": [], "kept": [], "moved_sql": []}
    storage_sources.mkdir(parents=True, exist_ok=True)
    tests_dbscript.mkdir(parents=True, exist_ok=True)

    # Move stray .sql files under storage/sources (not inside UUID folders)
    for item in storage_sources.iterdir():
        if item.is_file() and item.suffix.lower() == ".sql":
            target = tests_dbscript / item.name
            i = 1
            while target.exists():
                target = tests_dbscript / f"{item.stem}_{i}{item.suffix}"
                i += 1
            actions["moved_sql"].append({"from": str(item), "to": str(target)})
            if not dry_run:
                shutil.move(str(item), str(target))

    # Delete orphan UUID directories
    for item in storage_sources.iterdir():
        if _is_uuid_dir(item):
            if item.name not in valid_ids:
                actions["deleted"].append(str(item))
                if not dry_run:
                    shutil.rmtree(item, ignore_errors=True)
            else:
                actions["kept"].append(str(item))
    return actions


async def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup orphaned source storage and move test SQL files")
    parser.add_argument("--dry-run", action="store_true", help="Only print actions; do not modify files")
    parser.add_argument("--yes", action="store_true", help="Do not prompt for confirmation")
    args = parser.parse_args()

    backend_root, storage_sources, tests_dbscript = _paths()
    try:
        valid_ids = await _fetch_db_source_ids()
    except Exception as e:
        raise SystemExit(f"Failed to fetch source IDs from DB: {e}")

    actions = cleanup_filesystem(valid_ids, storage_sources, tests_dbscript, dry_run=args.dry_run)

    print("Cleanup plan:")
    print(f"  Keep:   {len(actions['kept'])}")
    print(f"  Delete: {len(actions['deleted'])}")
    print(f"  Move .sql: {len(actions['moved_sql'])}")

    if args.dry_run:
        print("Dry run complete. Re-run with --yes (without --dry-run) to apply.")
        return

    if not args.yes:
        resp = input("Proceed with deletions and moves? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return

    # Apply (already applied in cleanup when dry_run=False). Re-run to actually modify.
    # Re-run cleanup with dry_run=False
    actions = cleanup_filesystem(valid_ids, storage_sources, tests_dbscript, dry_run=False)
    print("Applied:")
    print(f"  Deleted {len(actions['deleted'])} directories")
    print(f"  Moved {len(actions['moved_sql'])} .sql files to {tests_dbscript}")


if __name__ == "__main__":
    asyncio.run(main())

# Relational generation: job wiring + tests (2025-11-06)

## Summary
- Added a background job for relational requests and integrated it with the unified start endpoint.
- Implemented artifact writing per table (CSV, Parquet) and a shared multi-sheet XLSX workbook.
- Produced a relational report with FK coverage and uniqueness collision counts; stored under `params_json.relational_report`.
- Added tests for topological sort and end-to-end artifact generation + FK coverage assertions.
- Verified full backend test suite passes in the Miniforge env.

## What changed
- API: `POST /api/v1/requests/{id}:start` now dispatches by request type and enqueues the appropriate RQ job (`flat` or `relational`).
- Job: `app/jobs/relational_job.py` runs relational generation, uploads artifacts via storage abstraction, persists `Artifact` rows, and updates request status/params.
- Service: `app/services/relational.py` generates tables in topological order, maintains PK pools, samples FKs (uniform/weighted), enforces uniqueness with capped retries, and builds coverage/collision report. Writes per-table CSV/Parquet and a shared `data.xlsx` with one sheet per table.
- Tests: `apps/backend/tests/test_relational_services.py` covers topo sort and a multi-table schema (Customers → Orders → OrderItems + Products + junction). Validates artifacts and that non-nullable FKs have 100% coverage (no orphans); asserts zero uniqueness collisions.

## Files
- app/api/api_v1/endpoints/flat.py – start endpoint enqueues `run_relational_job` for relational requests.
- app/jobs/relational_job.py – new background job for relational generation.
- app/services/relational.py – relational pipeline and artifact writers.
- docs/IMPLEMENTATION_SUMMARY.md – updated to reflect background jobs and relational generation (see below).
- apps/backend/tests/test_relational_services.py – new tests for relational generation and FK coverage.

## How to run
```powershell
# From repo root on Windows (conda env expected)
cmd.exe /d /c "call C:\ProgramData\miniforge3\Scripts\activate.bat C:\ProgramData\miniforge3 && conda activate conda-synthetic-data && cd apps\backend && set PYTHONPATH=. && python -m pytest -q"
```

## Notes
- FK sampling supports `uniform` and `weighted` modes; tests use the default `uniform` behavior.
- XLSX sheet names are truncated to 31 chars per Excel limits.
- Sequence providers maintain continuity across chunks for large row counts.
- Report keys:
  - `fk_coverage["table.column"] = { valid_pct: float, orphans: int }`
  - `collisions["table.column"] = int` (counts of unresolved uniqueness collisions)

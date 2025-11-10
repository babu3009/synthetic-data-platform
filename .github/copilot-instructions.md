# Copilot Instructions for Synthetic Data Platform

## Architecture Overview

This is a **monorepo** with FastAPI backend, React frontend, and supporting infrastructure for generating and managing synthetic relational/flat data.

```
apps/
├── backend/          # FastAPI + SQLAlchemy 2.x + Alembic
│   ├── app/          # Main application (api/, db/, services/, schemas/)
│   ├── synth/        # Provider-based data generation engine
│   └── alembic/      # Database migrations (schema: synthetic_data)
├── frontend/         # React 18 + Vite + TypeScript
infra/                # docker-compose for Postgres, Redis, MinIO
```

**Key invariant**: All database tables live in the **`synthetic_data` schema** (not `public`). Migrations and session config enforce `search_path=synthetic_data,public`.

## Database & Migrations (Alembic)

1. **Schema**: `synthetic_data` (defined in `app/db/base.py` as `SCHEMA_NAME`).
2. **ORM**: SQLAlchemy 2.x with async sessions (`AsyncSessionLocal` from `app/db/session.py`).
3. **Enum pattern**: Python `str, enum.Enum` classes map to PostgreSQL enum types (e.g., `RequestType`, `RequestStatus`, `LLMProviderKind`). When adding enum values, use `ALTER TYPE ... ADD VALUE` migrations to avoid recreation errors.
4. **Migration strategy**: Always create **additive migrations** (never edit old revisions). Use `batch_alter_table` for safe renames. When modifying enums, check if they exist (`create_type=False`) to prevent duplicates.
5. **Seeding**: `apps/backend/app/scripts/seed_db.py` uses idempotent logic (checks existence before insert) for LLM assets and project members. Other entities are created unconditionally and may duplicate on reruns (acceptable for demo data).

**Critical migration commands**:
```bash
# From apps/backend:
alembic upgrade head               # Apply all pending migrations
alembic revision --autogenerate -m "description"  # Generate new migration
python app/scripts/seed_db.py      # Populate demo data (idempotent for LLM/members)
python app/scripts/verify_counts.py  # Verify row counts across tables
```

## Data Generation Engine (`synth/`)

The platform generates synthetic data using a **provider-based architecture**:

- **Providers** (`synth/providers/`): Pluggable generators (faker, pattern, sequence, categorical, expression, geo, checksum, reference, empirical). Each provider implements `__call__(n: int, context: Context) -> List[Any]`.
- **Registry** (`synth/providers/registry.py`): Factory for instantiating providers from JSON config. Supports PII catalog shortcuts (e.g., `"email"` → faker email config).
- **Relational engine** (`app/services/relational.py`): Topologically sorts tables by FK dependencies, generates parent tables first, samples parent keys for FKs (uniform or weighted), enforces uniqueness/constraints, and emits rows in chunks.
- **Writers** (`app/services/writers.py`): Supports CSV, Parquet, XLSX, JSONL, Postgres upsert, and Kafka events. Configured via `request.params_json.outputs`.

**Example provider config** (in entity column):
```json
{
  "type": "faker",
  "method": "email",
  "unique": true
}
```

**Relational generation flow**:
1. Parse entity schema → extract tables, columns, FKs, PKs.
2. Topological sort by FK dependencies.
3. For each table: build providers, generate rows, resolve FK references from parent pools.
4. Write outputs (file + optional DB/Kafka).
5. Generate HTML validation report (optional: histograms, FK graph).

## API Patterns

### Async dependency injection
```python
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/example")
async def handler(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    return result.scalars().all()
```

### Error handling
Use FastAPI's `HTTPException` for user-facing errors. For internal failures, log and re-raise or return 500.

### Project-scoped resources
Most endpoints require `project_id` path param. Verify project existence before accessing child resources (sources, requests, api_keys).

### LLM integration
- Admin endpoints (`/api/v1/admin/llm/*`) require OWNER role + `project_id` query param.
- Flow: create provider → upsert credentials → probe connectivity → discover models → set project LLM settings.
- Inference endpoint (`/api/v1/projects/{id}/infer/providers`) rate-limited (default 60 RPM).

## Frontend Conventions

- **Routing**: React Router v6 with v7 future flags enabled (`v7_startTransition`, `v7_relativeSplatPath`).
- **State**: TanStack Query (React Query) for server state; React Hook Form + Zod for forms.
- **Validation**: Zod schemas in `src/types/schema.ts` shared across components.
- **Wizard**: Multi-step wizard for entity creation (Entities → Diagram → Providers → Rules → Outputs → Run). Auto-save via localStorage; dirty guard warns on navigation.
- **Accessibility**: Keyboard navigation in Diagram (Tab, Space, E, Arrow keys) and Providers grid (Alt+Up/Down). Visible focus outlines.
- **Charts**: Recharts for analytics, ReactFlow for FK diagrams.

## Testing

### Backend (pytest)
```bash
cd apps/backend
pytest -q                           # Run all tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=80  # Coverage
```
- Use `pytest-asyncio` for async tests.
- Test DB: `TESTING_DB_SCHEMA=testing_synthetic_data` (auto-isolated).

### Frontend (Vitest)
```bash
cd apps/frontend
pnpm test                           # Run all tests
pnpm coverage                       # Coverage
```
- Testing Library + user-event APIs (no `act` warnings).
- Vitest `provider: 'v8'` for coverage.

### Notifications (PowerShell)
```bash
make backend-test-notify            # Runs backend tests with toast/beep on completion
```

## Critical Conventions

### Enum value mismatch (common pitfall)
ORM enum classes define **lowercase** values (e.g., `LLMProviderKind.OPENAI = "openai"`), but some migrations added **uppercase** variants for compatibility. Always use `.value` when inserting via raw SQL or ensure ORM handles conversion. Current enums:
- `llmproviderkind`: lowercase `openai`, `anthropic`, etc. (plus uppercase `OPENAI` for legacy).
- `projectrole`: uppercase `OWNER`, `EDITOR`, `VIEWER`.

### Async session commits
Always `await db.commit()` after inserts/updates. Use `await db.refresh(obj)` to populate generated IDs/defaults.

### Schema search path
All SQL must reference `synthetic_data.*` or rely on session `search_path`. Migrations enforce schema via `op.*(..., schema=SCHEMA)`.

### Idempotency for seeding
LLM providers, models, settings, and project members check existence before insert. Projects, sources, requests, configs, artifacts do not (acceptable for demo seeding).

## Development Workflow

1. **Start infra**: `make infra-up` (Postgres, Redis, MinIO).
2. **Apply migrations**: `cd apps/backend && alembic upgrade head`.
3. **Seed demo data**: `python app/scripts/seed_db.py`.
4. **Start backend**: `make backend-dev` (http://localhost:8000).
5. **Start frontend**: `make frontend-dev` (http://localhost:3000).
6. **Run tests**: `make test` or per-app targets.
7. **Lint/format**: `make lint` / `make fmt`.

## CI/CD & Quality Gates

- **GitHub Actions**: `.github/workflows/ci.yml` runs linting, tests, coverage, security scans, OpenAPI drift checks, and builds Docker images.
- **Coverage gates**: Codecov project/patch >= 80% (enforced in CI).
- **Secret scanning**: `.secrets.allowlist` baseline to reduce false positives.
- **Test ordering drift**: Snapshots test execution order; CI fails on >10% drift.
- **SBOM & signing**: Images signed with cosign; SBOM artifacts uploaded.
- **SLO dashboard**: Aggregates coverage, flakiness, durations, cache hits, deps, security, image sizes into `slo-dashboard.{json,md}`.

## Key Files & Entry Points

- **Backend main**: `apps/backend/app/main.py` (FastAPI app instance).
- **API router**: `apps/backend/app/api/api_v1/api.py` (includes all endpoint routers).
- **Models**: `apps/backend/app/db/models.py` (SQLAlchemy ORM).
- **Session factory**: `apps/backend/app/db/session.py` (`AsyncSessionLocal`, `get_db` dependency).
- **Config**: `apps/backend/app/core/config.py` (Pydantic Settings from `.env`).
- **Relational engine**: `apps/backend/app/services/relational.py` (topological sort + FK resolution).
- **Provider registry**: `apps/backend/synth/providers/registry.py` (factory for data generators).
- **Frontend main**: `apps/frontend/src/main.tsx` (React entry + Router setup).
- **Wizard**: `apps/frontend/src/pages/projects/Wizard.tsx` (multi-step entity creation).

## Common Tasks

### Add a new migration
```bash
cd apps/backend
alembic revision --autogenerate -m "add_new_column"
# Edit generated migration, then:
alembic upgrade head
```

### Add a new provider
1. Implement in `apps/backend/synth/providers/providers.py` (inherit `BaseProvider`).
2. Register in `apps/backend/synth/providers/registry.py` (`from_config` factory).
3. Add to frontend provider dropdown (`apps/frontend/src/types/schema.ts`).

### Add a new API endpoint
1. Create handler in `apps/backend/app/api/api_v1/endpoints/`.
2. Include router in `apps/backend/app/api/api_v1/api.py`.
3. Add Pydantic schemas to `apps/backend/app/schemas/`.
4. Wire frontend hook in `apps/frontend/src/services/api.ts`.

### Debug DB issues
```bash
cd apps/backend
python debug_config.py              # Verify settings load
python test_db_connection.py        # Test DB connectivity
python list_databases.py            # List available databases
python app/scripts/verify_counts.py # Check table row counts
```

### Source Storage Cleanup (Maintenance)

Ephemeral test runs and ad-hoc uploads create many UUID-named folders under `apps/backend/storage/sources/`. Each folder should correspond to a `Source.id` in the `synthetic_data.sources` table. Orphaned folders (no matching DB row) accumulate over time and can be safely deleted.

Rules:
- Only keep directories whose name matches a current `Source.id` UUID in the database.
- Any loose `.sql` files directly under `storage/sources/` are considered test fixtures and must be moved to `apps/backend/tests/dbscript/`.
- New test DDL/SQL fixtures belong in `apps/backend/tests/dbscript/`.

Maintenance script:
```bash
cd apps/backend
python -m scripts.cleanup_orphan_sources --dry-run  # Show planned deletions/moves
python -m scripts.cleanup_orphan_sources --yes      # Apply deletions and moves
```
Behavior:
- Deletes orphan UUID directories.
- Moves stray top-level `.sql` files into `tests/dbscript/` (adds numeric suffix if name collision).
- Supports `--dry-run` for preview and `--yes` to skip interactive confirmation.

In CI or scheduled maintenance, run with `--yes` after a dry-run log capture.


## External Dependencies & Integration

- **PostgreSQL 15**: Primary datastore (schema: `synthetic_data`).
- **Redis 7**: Cache + RQ queue for background jobs.
- **MinIO**: S3-compatible storage for artifacts (CSV, Parquet, XLSX, JSONL, HTML reports).
- **LLM providers**: OpenAI, Anthropic, Ollama, LMStudio (optional; configured via admin endpoints).
- **Postgres write-back**: Optional output mode for upserting generated rows into external DB (via `params_json.outputs.db`).
- **Kafka events**: Optional output mode for publishing rows as JSON events (via `params_json.outputs.kafka`).

## Configuration

All backend config lives in `apps/backend/.env` (see `.env.example` for template). Key vars:
- `DB_SCHEMA=synthetic_data` (required).
- `POSTGRES_*`: Database connection.
- `REDIS_*`: Redis connection.
- `MINIO_*`: MinIO/S3 credentials.
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.: LLM provider keys (optional).
- `ENABLE_METRICS=true`: Expose Prometheus metrics at `/metrics`.
- `ENABLE_TRACING=false`: OTEL tracing (set endpoint to enable).

Frontend config in `apps/frontend/.env` (minimal; mainly `VITE_API_BASE_URL`).

## Performance & Scaling

- **Batch writes**: Relational engine emits rows in chunks (default 10K) to reduce memory.
- **Topological sorting**: Ensures parent tables generated before children (supports cycles via fallback to input order).
- **FK sampling**: Weighted mode reuses parent keys proportionally; uniform mode samples evenly.
- **Parallel generation**: Not yet implemented (single-threaded per request; scale via worker concurrency).

## Debugging Tips

1. **Migration conflicts**: Use `alembic history` to inspect revision chain; `alembic downgrade <rev>` to rollback.
2. **Enum errors**: Check if DB enum matches ORM enum values (case-sensitive). Use `\dT+ llmproviderkind` in psql.
3. **FK resolution failures**: Verify parent table generated first in topo order; check parent pool non-empty.
4. **Async session issues**: Always `await` on queries/commits; use `db.refresh()` after insert.
5. **Frontend API errors**: Inspect Network tab; verify API base URL (`VITE_API_BASE_URL`).

## Security Notes

- **API keys**: Hashed with server-side pepper (`SECRET_KEY` + SHA-256).
- **OIDC**: Optional login via OpenID Connect (configure `OIDC_*` vars).
- **CORS**: Controlled via `BACKEND_CORS_ORIGINS` (default localhost:3000, 8000).
- **Rate limiting**: Inference endpoint rate-limited (`INFER_RATE_LIMIT_PER_MINUTE`).
- **Trivy scans**: CI scans Docker images for CVEs (fails on HIGH/CRITICAL).
- **Secret scanning**: Detect-secrets baseline in `.secrets.allowlist`.

## Observability

- **Metrics**: `/metrics` endpoint (Prometheus format; counters: `synth_requests_*`).
- **Tracing**: OTEL export via `OTEL_EXPORTER_OTLP_ENDPOINT` (optional).
- **Logs**: Structured JSON logs (`LOG_LEVEL=info`).
- **Audit events**: Tracked in `audit_events` table (project-scoped).
- **Validation reports**: HTML artifacts with stats, FK graphs, histograms (generated post-run).

## References

- **Main docs**: `README.md`, `docs/PROJECT_SUMMARY.md`, `docs/BACKEND_DATABASE.md`, `docs/LLM_DISCOVERY.md`, `docs/TESTING.md`.
- **Task tracker**: `TODO.md` (canonical list of open/completed work).
- **API docs**: http://localhost:8000/docs (auto-generated OpenAPI).
- **Makefile**: Run `make help` for all available commands.

# Synthetic Data Platform

A modern monorepo for generating and managing synthetic data using FastAPI, React, and supporting infrastructure.

## Architecture

```
synthetic-data-platform/
├── apps/
│   ├── backend/          # FastAPI application
│   └── frontend/         # React + Vite application
├── infra/               # Infrastructure configuration
├── .devcontainer/       # Development container setup
└── .github/workflows/   # CI/CD pipelines
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Poetry (for Python dependency management)
- pnpm (for Node.js dependency management)

### Development Setup

1. **Clone and setup the repository:**
   ```bash
   git clone <repository-url>
   cd synthetic-data-platform
   ```

2. **Start infrastructure services:**
   ```bash
   make infra-up
   ```

3. **Setup backend:**
   ```bash
   make backend-setup
   make backend-dev
   ```

4. **Setup frontend:**
   ```bash
   make frontend-setup
   make frontend-dev
   ```

### Available Commands

```bash
# Development
make dev              # Start all services in development mode
make backend-dev      # Start backend development server
make frontend-dev     # Start frontend development server

# Infrastructure
make infra-up         # Start infrastructure services (Postgres, Redis, MinIO)
make infra-down       # Stop infrastructure services

# Testing
make test             # Run all tests
make backend-test     # Run backend tests
make frontend-test    # Run frontend tests

# Code Quality
make lint             # Run all linters
make fmt              # Format all code
make type-check       # Run type checking

# Database
make migrate          # Run database migrations
make seed             # Seed database with sample data
```

## Services

- **Backend API**: http://localhost:8000
  - Health check: http://localhost:8000/health
  - API docs: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **MinIO**: http://localhost:9000 (admin: minioadmin/minioadmin)

## Technology Stack

### Backend
- FastAPI (Python 3.11)
- Pydantic v2
- SQLAlchemy 2.x
- Alembic (migrations)
- RQ (Redis Queue)
- uvicorn (ASGI server)
- pyarrow, pandas, openpyxl (data processing)
- faker, mimesis (synthetic data generation)

### Frontend
- React 18
- Vite (build tool)
- TypeScript
- Bootstrap 5
- React Router
- React Query (TanStack Query)
- React Hook Form
- Zod (runtime schemas and validation)
- Recharts (charts)
- ReactFlow (flow diagrams)

#### Wizard features
- Entities: create/import via DDL or JSON; manual field designer
- Diagram: visualize tables and relationships; auto-layout with ReactFlow
- Providers & PII: per-column provider selection (faker, pattern, sequence, categorical, expression, geo, checksum-valid, reference, empirical), JSON config with inline validation, PII toggle with subtype, bulk auto-suggest via backend with confirmation diff, and save
- Rules: split editor for YAML/JSON rules with inline linting (implication, uniqueness, distribution, temporal), one-click dry-run validation via POST /api/v1/validate with compact report for sample vs final data
- Outputs & Run: pick output formats (CSV/XLSX/Parquet/JSONL), destination, optional schedule; compute estimates via `POST /api/v1/projects/{project_id}/requests/{request_id}:estimate`; create and start requests; navigate to Request Detail with live status polling and artifact links (`GET /api/v1/requests/{request_id}/artifacts`).

#### Outputs: files, Postgres upsert, Kafka events
- File artifacts: CSV/Parquet/XLSX/JSONL are written chunk-wise and uploaded to MinIO (or local storage fallback) as `s3://<bucket>/requests/{requestId}/...`.
- Postgres write-back (optional): enable via request `params_json.outputs.db`:
   - `enabled`: boolean
   - `dsn`: `postgresql+psycopg2://user:pass@host:5432/db`
   - `table_map`: object mapping tableName -> target fully-qualified table (or use `table_prefix`)
   - `conflict_columns_map`: object mapping tableName -> array of conflict columns (defaults to PK columns)
   - `batch_size` (optional, default 10k)
   Rows are inserted using `INSERT ... ON CONFLICT (...) DO UPDATE`, batched and wrapped in a single transaction per request.
- Kafka publish (optional): enable via request `params_json.outputs.kafka`:
   - `enabled`: boolean
   - `brokers`: array or comma-separated string
   - `topic`: topic name
   - `key_field`: column name to use as partition key (optional)
   - `headers`: map of string headers (optional)
   - `linger_ms`, `batch_size`, `acks` (optional producer tuning)
   Events are JSON-serialized rows; set `include_table_name: true` to add `__table__` to each payload.

   For full configuration details and curl examples, see `apps/backend/docs/OUTPUTS.md`.

#### Accessibility and performance
- Keyboard navigation:
   - Diagram: Tab to focus columns, Space/Enter toggles PK, E opens editor, Arrow keys move between rows.
   - Providers grid: Alt+ArrowUp/Alt+ArrowDown moves focus to the same control in the previous/next row.
- Visible focus outlines: Bootstrap-compatible :focus-visible and focus ring styles improve discoverability for keyboard users.
- Tooltips: Contextual help for PK/FK, row targets (absolute/ratioTo), Providers (Provider/Config/PII), and Distribution fields.
- Performance: Diagram table node column lists are windowed (paged) for large schemas; Column Editor modal is lazy-loaded to reduce initial bundle size.

#### Saving and drafts
- Autosave: Diagram and Providers tabs autosave after ~800ms of inactivity (best-effort, localStorage fallback).
- Dirty guard: the wizard warns when navigating away with unsaved changes; tab switches prompt for confirmation.
- Draft mode: partially defined entities are preserved per project and rehydrated on load so users can return later.

### Client types and hooks

- Shared types and Zod schemas live in `apps/frontend/src/types/schema.ts` and cover entities, tables/columns, relationships, providers, distributions, and rule definitions.
- React Query hooks centralize data access and cache invalidation:
   - `useEntities(projectId)` for list/create/update/delete with cache keys like `['entities', projectId]`
   - `useSources(projectId)` for source uploads (DDL/JSON) and schema fetching
   - `useInferProviders(projectId)` to call backend auto-suggest for provider configs
   - `useValidate(projectId)` to dry-run validate Rules payloads against the backend

### Infrastructure
- PostgreSQL 15
- Redis 7
- MinIO (S3-compatible storage)
- Docker & Docker Compose

### Code Quality
- **Backend**: ruff, black, mypy, pytest
- **Frontend**: ESLint, Prettier, TypeScript
- **Pre-commit hooks**: Automated code quality checks
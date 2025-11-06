# Backend Database Quick Start Guide

This guide will help you set up and run the Synthetic Data Platform backend with the newly implemented database models and API endpoints.

## Prerequisites

Before starting, ensure you have the following installed:
- Python 3.11+
- Poetry (for dependency management) or pip
- Docker and Docker Compose (for infrastructure)
- PostgreSQL client tools (optional, for debugging)

## Quick Start

### 1. Install Dependencies

Using Poetry (recommended):
```bash
cd apps/backend
poetry install
```

Using pip:
```bash
cd apps/backend
pip install -r requirements.txt  # You'll need to generate this from pyproject.toml
```

### 2. Start Infrastructure Services

From the project root:
```bash
cd infra
docker-compose up -d
```

This starts:
- PostgreSQL 15 (localhost:5432)
- Redis 7 (localhost:6379)
- MinIO (localhost:9000, console: localhost:9001)

Wait a few seconds for the services to be ready.

### 3. Configure Environment

Copy `apps/backend/.env.example` to `apps/backend/.env` and set at least:

- `SECRET_KEY` (required) – a strong random value
- Optional OIDC settings to enable login redirect/callback:
  - `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`, `OIDC_SCOPES`

See also `apps/backend/docs/SECURITY.md` for details on authentication, API keys, and RBAC.

### 4. Generate Initial Migration

From the backend directory:
```bash
cd apps/backend
poetry run alembic revision --autogenerate -m "Initial migration with core models"
```

Or use the setup script:
```bash
python setup_db.py
```

### 5. Run Migrations

Apply the migration to create all database tables:
```bash
poetry run alembic upgrade head
```

### 6. Seed Sample Data

Populate the database with sample data:
```bash
poetry run python -m app.scripts.seed_db
```

This creates:
- 3 sample projects
- 4 sample sources
- 4 sample requests (with different statuses)
- 3 sample configurations
- 3 sample artifacts

### 7. Start the Backend Server

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

API Documentation (Swagger): http://localhost:8000/docs

### 8. Verify Installation

Run the validation script:
```bash
python validate_implementation.py
```

You should see all 23 components marked as ✅.

## API Endpoints

### Projects

- `POST /api/v1/projects/` - Create a new project
- `GET /api/v1/projects/` - List all projects
- `GET /api/v1/projects/{id}` - Get specific project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Requests

- `POST /api/v1/projects/{project_id}/requests/` - Create generation request
- `GET /api/v1/projects/{project_id}/requests/` - List project requests
- `GET /api/v1/projects/{project_id}/requests/{id}` - Get specific request
- `POST /api/v1/projects/{project_id}/requests/{id}:estimate` - Estimate size/time for a request
- `POST /api/v1/requests/{id}:start` - Start a pending request

### Artifacts
- `GET /api/v1/auth/login` – Returns OIDC authorize URL (scaffold)
- `GET /api/v1/auth/callback` – Verifies `id_token` if provided (scaffold)
- `GET /api/v1/projects/{project_id}/api-keys/` – List API keys (OWNER)
- `POST /api/v1/projects/{project_id}/api-keys/` – Create API key (OWNER; returns plaintext once)
- `DELETE /api/v1/projects/{project_id}/api-keys/{key_id}` – Revoke API key (OWNER)

See `apps/backend/docs/SECURITY.md` for auth model, scopes, and roles.

- `GET /api/v1/requests/{request_id}/artifacts` - List request artifacts
- `GET /api/v1/requests/{request_id}/artifacts/{id}` - Get specific artifact

### Providers & PII
- `POST /api/v1/projects/{project_id}/infer/providers` – Bulk provider suggestions for a set of columns (RBAC/Scopes enforced).
- `POST /api/v1/infer/providers` – Non-scoped alias for suggestions when project context is not required.
- `PUT /api/v1/projects/{project_id}/entities/{entity_id}/providers` – Save per-entity provider configuration (PII flags, subtypes, and provider configs).

Request body for infer endpoints:

```json
{
  "columns": [
    {"table": "customers", "column": "id", "dtype": "uuid"},
    {"table": "customers", "column": "email", "dtype": "text"},
    {"table": "orders", "column": "amount", "dtype": "numeric"}
  ],
  "llm": {"enabled": false, "provider": "openai", "model": "gpt-4o-mini"}
}
```

Fields:
- `columns.*.dtype` and `columns.*.description` are optional hints that help heuristics.
- `llm` is optional; when enabled and credentials are present, ambiguous confidences may be nudged slightly. Supported providers: `openai`, `anthropic`, `ollama`, `lmstudio`.

Environment variables for LLMs (optional):
- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Anthropic
- Local providers (`ollama`, `lmstudio`) assume their default local endpoints if selected.

#### Example: Infer Providers (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/infer/providers" \
  -H "Content-Type: application/json" \
  -d '{
    "columns": [
      {"table": "customers", "column": "id", "dtype": "uuid"},
      {"table": "customers", "column": "email", "dtype": "text"}
    ],
    "llm": {"enabled": false}
  }'
```

#### Example: Save Providers (curl)

```bash
curl -X PUT "http://localhost:8000/api/v1/projects/${PROJECT_ID}/entities/${ENTITY_ID}/providers" \
  -H "Content-Type: application/json" \
  -d '{
    "providers": [
      {"table":"customers","column":"email","provider":"faker","providerConfig":{"method":"email"},"pii":true,"piiSubtype":"email"}
    ]
  }'
```

### LLM Administration (OWNER)

LLM providers, credentials, and models are managed via admin endpoints. These routes require the caller to be an OWNER for a project; provide `?project_id=<uuid>` as a query parameter to establish RBAC scope.

Endpoints:

- `GET /api/v1/admin/llm/providers?project_id={project_id}` – List providers
- `POST /api/v1/admin/llm/providers?project_id={project_id}` – Create provider
- `PATCH /api/v1/admin/llm/providers/{provider_id}?project_id={project_id}` – Update provider
- `POST /api/v1/admin/llm/providers/{provider_id}/credentials?project_id={project_id}` – Upsert credentials (secrets masked in audit)
- `GET /api/v1/admin/llm/providers/{provider_id}/models?project_id={project_id}` – List models
- `POST /api/v1/admin/llm/providers/{provider_id}/models?project_id={project_id}` – Create model
- `POST /api/v1/admin/llm/providers/{provider_id}:probe?project_id={project_id}` – Probe provider (no-op stub now)
- `POST /api/v1/admin/llm/providers/{provider_id}:discover-models?project_id={project_id}` – Discover models (placeholder)

Example payloads:

Create provider

```json
{
  "kind": "openai",
  "name": "openai",
  "base_url": "https://api.openai.com/v1",
  "is_enabled": true
}
```

Upsert credentials (server stores encrypted/encoded payload; response never returns the secret):

```json
{
  "enc_payload_json": "<encrypted-secret>"
}
```

Create model

```json
{
  "name": "gpt-4o-mini",
  "display_name": "GPT-4o Mini",
  "context_tokens": 128000,
  "supports_json": true,
  "is_default": true,
  "metadata_json": {"family": "gpt", "tier": "standard"}
}
```

Audit: All admin mutations persist `AuditEvent` with masked values (e.g., secrets replaced by placeholders).

### Project LLM Settings

Per-project defaults for LLM usage, including selected provider/model and tuning parameters.

Endpoints:

- `GET /api/v1/projects/{project_id}/llm-settings` – Read settings (VIEWER+). Returns defaults when not configured.
- `PUT /api/v1/projects/{project_id}/llm-settings` – Create/update settings (EDITOR+). Emits `AuditEvent` on change.

Example payload:

```json
{
  "enabled": true,
  "provider_id": "<uuid>",
  "model_id": "<uuid>",
  "temperature": 0.2,
  "top_p": 1.0,
  "max_tokens": 512,
  "guardrails_json": {"block_pii": true}
}
```

### Rules Validation (On-demand)
- `POST /api/v1/validate` – Runs validations without persistence; returns normalized rules and a compact report for `sample` and `final` datasets.

Body shape (abbreviated):

```json
{
  "rules": [
    {"when":"orders.total > 1000","then":["orders.channel in ['WEB','PARTNER']"]},
    {"uniqueness": ["customers.email"]},
    {"distribution": {"product.category": {"A":0.5,"B":0.3,"C":0.2}}},
    {"temporal": "shipment.promised_date <= shipment.order_date + 2d"}
  ],
  "data_sample": {"orders": [{"id":1,"total":1500,"channel":"WEB"}]},
  "data_final": {"orders": [{"id":2,"total":1200,"channel":"STORE"}]},
  "max_violations": 10
}
```

For more details (normalized types and examples), see `docs/tasks/2025-11-06-frontend-integration-notes.md` and `docs/tasks/2025-11-06-rules-validation.md`.

#### Example: Validate Rules (curl)

```bash
curl -X POST "http://localhost:8000/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [
      {"when":"orders.total > 1000","then":["orders.channel in [''WEB'',''PARTNER'']"]},
      {"uniqueness": ["customers.email"]}
    ],
    "data_sample": {"orders": [{"id": 1, "total": 1500, "channel": "WEB"}]},
    "data_final": {"orders": [{"id": 2, "total": 1200, "channel": "STORE"}]},
    "max_violations": 10
  }'
```

### Request Lifecycle Examples

#### Create Request

```bash
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/requests/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "relational",
    "seed": 42,
    "params_json": {"rows": 1000, "tables": ["users","orders"]}
  }'
```

#### Estimate Request

```bash
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/requests/${REQUEST_ID}:estimate"
```

#### Start Request

```bash
curl -X POST "http://localhost:8000/api/v1/requests/${REQUEST_ID}:start"
```

#### Get Request Status

```bash
curl "http://localhost:8000/api/v1/projects/${PROJECT_ID}/requests/${REQUEST_ID}"
```

#### List Artifacts

```bash
curl "http://localhost:8000/api/v1/requests/${REQUEST_ID}/artifacts"
```

## Example API Calls

### Create a Project

```bash
curl -X POST "http://localhost:8000/api/v1/projects/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Project",
    "owner": "user@example.com",
    "tags": ["test", "demo"]
  }'
```

### List Projects

```bash
curl "http://localhost:8000/api/v1/projects/"
```

### Create a Request

```bash
curl -X POST "http://localhost:8000/api/v1/projects/{project_id}/requests/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "relational",
    "seed": 42,
    "params_json": {
      "rows": 1000,
      "tables": ["users", "orders"]
    }
  }'
```

## Running Tests

### Run All Tests

```bash
cd apps/backend
poetry run pytest
```

Note: When PostgreSQL is unavailable, the test suite falls back to a local SQLite database at the repository root under `testing/databases/test.db`. The test harness creates this path automatically if it doesn't exist.

### Run Specific Test File

```bash
poetry run pytest tests/test_models.py
poetry run pytest tests/test_crud.py
poetry run pytest tests/test_api.py
```

### Run with Coverage

```bash
poetry run pytest --cov=app --cov-report=html
```

## Database Management

### View Database

Connect to PostgreSQL:
```bash
docker exec -it synthetic-data-postgres psql -U postgres -d synthetic_data_platform
```

Useful SQL commands:
```sql
-- List all tables
\dt

-- View projects
SELECT * FROM projects;

-- View requests with project names
SELECT r.*, p.name as project_name 
FROM requests r 
JOIN projects p ON r.project_id = p.id;

-- View artifacts with request info
SELECT a.*, r.type as request_type, r.status 
FROM artifacts a 
JOIN requests r ON a.request_id = r.id;
```

## Database configuration and schema selection

This backend supports two ways to configure the database connection:

- DATABASE_URL (recommended): a full SQLAlchemy URL; when set, it takes precedence over individual POSTGRES_* fields.
- POSTGRES_* fields: host/user/password/db/port used to construct an async URL when DATABASE_URL is not provided.

Example DATABASE_URL (async, using asyncpg):

```powershell
# PowerShell example
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/synthetic_data_platform"
```

If DATABASE_URL is not set, the URL is built from these variables:

```text
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=synthetic_data_platform
POSTGRES_PORT=5432
```

### Schema selection

- DB_SCHEMA: The application schema used in normal (development/production) runs. Defaults to `synthetic_data`.
- TESTING_DB_SCHEMA: Optional separate schema used when tests run. If set, tests prefer this schema to keep test data isolated from your main schema.

When tests execute, the app’s metadata will target TESTING_DB_SCHEMA (if provided); otherwise it will continue to use DB_SCHEMA.

You can pre-create the testing schema and its tables using the helper script:

```powershell
cd apps/backend
$env:PYTHONPATH = '.'
python scripts/create_testing_schema.py
```

Notes:

- The application uses async drivers (asyncpg). For admin tooling/migrations that need sync drivers, the code constructs a sync URL by replacing `+asyncpg` with `+psycopg2` where appropriate.
- For Postgres multi-schema setups, the engines set `search_path` to "<schema>, public" so queries target the configured schema.

### Reset Database

To completely reset the database:
```bash
# From project root
cd infra
docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS synthetic_data_platform;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE synthetic_data_platform;"

# Then re-run migrations and seeding
cd ../apps/backend
poetry run alembic upgrade head
poetry run python -m app.scripts.seed_db
```

### Create New Migration

After modifying models:
```bash
poetry run alembic revision --autogenerate -m "Your migration message"
poetry run alembic upgrade head
```

## Database Schema

### Core Tables

1. **projects** - Project containers for organizing work
2. **sources** - Data sources/schemas for generation
3. **requests** - Synthetic data generation requests
4. **configs** - Versioned generation configurations
5. **artifacts** - Generated output files
6. **api_keys** - API authentication keys
7. **audit_events** - Audit trail for all actions

See [BACKEND_DATABASE.md](../../docs/BACKEND_DATABASE.md) for detailed schema documentation.

## Troubleshooting

### PostgreSQL Connection Issues

If you can't connect to PostgreSQL:
1. Check if the container is running: `docker ps`
2. Check PostgreSQL logs: `docker logs synthetic-data-postgres`
3. Verify the database exists: `docker exec synthetic-data-postgres psql -U postgres -l`

### Migration Issues

If migrations fail:
1. Check your model definitions in `app/db/models.py`
2. Ensure all models are imported in `alembic/env.py`
3. Try creating a manual migration: `alembic revision -m "manual"`

### Import Errors

If you get import errors:
1. Ensure you're in the backend directory: `cd apps/backend`
2. Activate the virtual environment: `poetry shell`
3. Verify installations: `poetry install`

### Test Failures

If tests fail:
1. Check that test database is isolated (using SQLite)
2. Ensure fixtures are properly defined in `conftest.py`
3. Run with verbose output: `pytest -vv`

## Development Workflow

### Typical Development Cycle

1. **Make Model Changes** - Edit `app/db/models.py`
2. **Update Schemas** - Edit Pydantic schemas in `app/schemas/`
3. **Update CRUD** - Modify CRUD operations in `app/crud/`
4. **Update API** - Modify endpoints in `app/api/api_v1/endpoints/`
5. **Create Migration** - `alembic revision --autogenerate -m "description"`
6. **Run Migration** - `alembic upgrade head`
7. **Write Tests** - Add tests in `tests/`
8. **Run Tests** - `pytest`
9. **Manual Testing** - Use Swagger UI at http://localhost:8000/docs

### Code Quality

Run linting and formatting:
```bash
poetry run ruff check .
poetry run black .
poetry run mypy .
```

## Next Steps

Now that the database is set up, you can:

1. **Implement Generation Engine** - Connect RQ for background job processing
2. **Add Authentication** - Implement JWT-based auth with API keys
3. **Connect MinIO** - Implement file storage for artifacts
4. **Build Frontend** - Connect React app to these APIs
5. **Add Monitoring** - Implement metrics and logging

## Additional Resources

- [Backend Database Documentation](../../docs/BACKEND_DATABASE.md) - Detailed schema and API docs
- [Project Summary](../../docs/PROJECT_SUMMARY.md) - Overall project structure
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework docs
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - SQLAlchemy ORM docs
- [Alembic Documentation](https://alembic.sqlalchemy.org/) - Database migration docs
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation docs

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

### 3. Generate Initial Migration

From the backend directory:
```bash
cd apps/backend
poetry run alembic revision --autogenerate -m "Initial migration with core models"
```

Or use the setup script:
```bash
python setup_db.py
```

### 4. Run Migrations

Apply the migration to create all database tables:
```bash
poetry run alembic upgrade head
```

### 5. Seed Sample Data

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

### 6. Start the Backend Server

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

API Documentation (Swagger): http://localhost:8000/docs

### 7. Verify Installation

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

### Artifacts

- `GET /api/v1/requests/{request_id}/artifacts` - List request artifacts
- `GET /api/v1/requests/{request_id}/artifacts/{id}` - Get specific artifact

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

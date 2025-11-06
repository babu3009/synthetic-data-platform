# Backend Database Implementation

This document describes the implemented database schema, API endpoints, and setup procedures for the Synthetic Data Platform backend.

Related documentation:

- `apps/backend/docs/OUTPUTS.md` – Configure file artifacts, Postgres upsert, and Kafka publishing

## Database Schema

### Models Overview

The database schema consists of 7 core models representing the synthetic data generation workflow:

#### 1. Project
- **Purpose**: Top-level container for organizing synthetic data projects
- **Fields**:
  - `id` (UUID, PK): Unique project identifier  
  - `name` (String): Project name
  - `owner` (String): Project owner email/identifier
  - `tags` (Array[String]): Project tags for categorization
  - `created_at` (DateTime): Creation timestamp

#### 2. Source
- **Purpose**: Defines source data/schema for synthetic generation
- **Fields**:
  - `id` (UUID, PK): Unique source identifier
  - `project_id` (UUID, FK): Reference to parent project
  - `kind` (Enum): Source type - `ddl|json|introspection`
  - `storage_uri` (String): URI to source data/schema
  - `checksum` (String): SHA-256 hash for integrity
  - `created_at` (DateTime): Creation timestamp

#### 3. Request
- **Purpose**: Represents a synthetic data generation request
- **Fields**:
  - `id` (UUID, PK): Unique request identifier
  - `project_id` (UUID, FK): Reference to parent project
  - `type` (Enum): Request type - `relational|flat|timeseries`
  - `status` (Enum): Current status - `pending|running|completed|failed|cancelled`
  - `seed` (Integer): Random seed for reproducibility
  - `params_json` (JSONB): Request parameters
  - `created_at` (DateTime): Creation timestamp
  - `started_at` (DateTime): Processing start time
  - `finished_at` (DateTime): Processing completion time

#### 4. Config
- **Purpose**: Versioned configuration for generation requests
- **Fields**:
  - `id` (UUID, PK): Unique config identifier
  - `request_id` (UUID, FK): Reference to parent request
  - `version` (Integer): Configuration version number
  - `body_json` (JSONB): Configuration body
  - `created_at` (DateTime): Creation timestamp

#### 5. Artifact
- **Purpose**: Generated synthetic data output files
- **Fields**:
  - `id` (UUID, PK): Unique artifact identifier
  - `request_id` (UUID, FK): Reference to parent request
  - `format` (Enum): File format - `csv|xlsx|parquet|jsonl`
  - `storage_uri` (String): URI to generated file
  - `size_bytes` (BigInteger): File size in bytes
  - `created_at` (DateTime): Creation timestamp

#### 6. ApiKey
- **Purpose**: API key management for project access control
- **Fields**:
  - `id` (UUID, PK): Unique key identifier
  - `project_id` (UUID, FK): Reference to associated project
  - `name` (String): Human-readable key name
  - `hashed_key` (String): Hashed API key value
  - `scopes` (Array[String]): Permission scopes
  - `created_at` (DateTime): Creation timestamp

#### 7. AuditEvent
- **Purpose**: Audit log for tracking user actions
- **Fields**:
  - `id` (UUID, PK): Unique event identifier
  - `actor` (String): User/system performing action
  - `project_id` (UUID, FK, nullable): Associated project (if applicable)
  - `action` (String): Action performed
  - `payload_json` (JSONB): Event details
  - `created_at` (DateTime): Event timestamp

### Relationships

- **Project** → **Source** (1:Many): Projects can have multiple data sources
- **Project** → **Request** (1:Many): Projects can have multiple generation requests
- **Project** → **ApiKey** (1:Many): Projects can have multiple API keys
- **Project** → **AuditEvent** (1:Many): Projects track all actions via audit events
- **Request** → **Config** (1:Many): Requests can have multiple configuration versions
- **Request** → **Artifact** (1:Many): Requests can generate multiple output artifacts

## API Endpoints

### Projects API (`/api/v1/projects`)

#### POST /projects
- **Purpose**: Create a new project
- **Request Body**: `ProjectCreate` schema
- **Response**: Created `Project`
- **Validation**: Prevents duplicate project names per owner

#### GET /projects
- **Purpose**: List projects with pagination
- **Query Parameters**: `skip` (int), `limit` (int)
- **Response**: Array of `Project` objects

#### GET /projects/{project_id}
- **Purpose**: Get specific project by ID
- **Path Parameters**: `project_id` (UUID)
- **Response**: `Project` object or 404

#### PUT /projects/{project_id}
- **Purpose**: Update project details
- **Path Parameters**: `project_id` (UUID)
- **Request Body**: `ProjectUpdate` schema
- **Response**: Updated `Project`

#### DELETE /projects/{project_id}
- **Purpose**: Delete project and all related data
- **Path Parameters**: `project_id` (UUID)
- **Response**: Deleted `Project` object

### Requests API (`/api/v1/projects/{project_id}/requests`)

#### POST /projects/{project_id}/requests
- **Purpose**: Create synthetic data generation request
- **Path Parameters**: `project_id` (UUID)
- **Request Body**: `RequestCreate` schema
- **Response**: Created `Request`
- **Status**: Initial status is `pending`

#### GET /projects/{project_id}/requests
- **Purpose**: List requests for a project
- **Path Parameters**: `project_id` (UUID)
- **Query Parameters**: `skip` (int), `limit` (int)
- **Response**: Array of `Request` objects

#### GET /projects/{project_id}/requests/{request_id}
- **Purpose**: Get specific request details
- **Path Parameters**: `project_id` (UUID), `request_id` (UUID)
- **Response**: `Request` object or 404

#### POST /projects/{project_id}/requests/{request_id}:estimate
- **Purpose**: Get a quick estimate of rows/size/time before running.
- **Path Parameters**: `project_id` (UUID), `request_id` (UUID)
- **Response**: `{ "rows": number, "size_bytes": number, "seconds": number }` (fields optional by engine)

#### POST /requests/{request_id}:start
- **Purpose**: Start processing a previously created request.
- **Path Parameters**: `request_id` (UUID)
- **Response**: Updated `Request` with status transitioning to `running`

### Artifacts API (`/api/v1/requests/{request_id}/artifacts`)

#### GET /requests/{request_id}/artifacts
- **Purpose**: List artifacts generated for a request
- **Path Parameters**: `request_id` (UUID)
- **Response**: Array of `Artifact` objects

#### GET /requests/{request_id}/artifacts/{artifact_id}
- **Purpose**: Get specific artifact details
- **Path Parameters**: `request_id` (UUID), `artifact_id` (UUID)
- **Response**: `Artifact` object or 404

### Providers & PII

#### POST /api/v1/projects/{project_id}/infer/providers
- **Purpose**: Infer per-column providers (and PII flags/subtypes) for a submitted entity schema.
- **Request Body**: Entity schema JSON (see integration notes).
- **Response**: `{ "suggestions": [{ table, column, provider, providerConfig, pii, piiSubtype }] }`

#### PUT /api/v1/projects/{project_id}/entities/{entity_id}/providers
- **Purpose**: Persist per-entity provider configuration.
- **Request Body**: `{ "providers": [{ table, column, provider, providerConfig, pii, piiSubtype }] }`
- **Response**: Updated summary or `204 No Content`.

### Rules Validation (On-demand)

#### POST /api/v1/validate
- **Purpose**: Run validation against provided datasets without persisting.
- **Request Body (abbreviated)**:
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
- **Response**: `{ "rules": [normalized...], "report": { "sample": [...], "final": [...] } }`

See `docs/tasks/2025-11-06-frontend-integration-notes.md` for detailed payloads and TypeScript types.

### Authentication and API Keys

#### OIDC (scaffold)
- `GET /api/v1/auth/login` – Returns provider authorize URL
- `GET /api/v1/auth/callback` – Verifies `id_token` using provider JWKS when supplied

Environment:
- `SECRET_KEY` (required), `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`, `OIDC_SCOPES`

#### API Key Management (OWNER role required)
- `GET /api/v1/projects/{project_id}/api-keys/` – List keys
- `POST /api/v1/projects/{project_id}/api-keys/` – Create key (returns plaintext once)
- `DELETE /api/v1/projects/{project_id}/api-keys/{key_id}` – Revoke key

Authorization model combines API key scopes with user RBAC; see `apps/backend/docs/SECURITY.md` for details.

## CRUD Operations

### Base CRUD Class
- **Generic Implementation**: `CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]`
- **Common Operations**: `get`, `get_multi`, `create`, `update`, `remove`
- **Async Support**: All operations use `AsyncSession`

### Specialized CRUD Classes
- **CRUDProject**: Project-specific operations (get by owner, check name uniqueness)
- **CRUDRequest**: Request-specific operations (get by project, filter by status)
- **CRUDArtifact**: Artifact-specific operations (get by request)

## Database Setup

### Alembic Configuration
- **Migration Directory**: `apps/backend/alembic/`
- **Config File**: `alembic.ini` with PostgreSQL connection
- **Environment**: Configured for async operations with proper model imports

### Migration Generation
```bash
# Create initial migration
cd apps/backend
poetry run alembic revision --autogenerate -m "Initial migration with core models"
```

### Database Commands (via Makefile)
```bash
# Run migrations
make migrate

# Create new migration
make migrate-create name="description"

# Seed database with sample data
make seed

# Reset database (drop/recreate/migrate/seed)
make db-reset
```

### Sample Data (Seeding)
The seed script (`app/scripts/seed_db.py`) creates:
- 3 sample projects with different owners and tags
- 4 sample sources with different kinds (DDL, JSON, introspection)
- 4 sample requests with various types and statuses
- 3 sample configurations with realistic generation parameters
- 3 sample artifacts in different formats

## Testing

### Test Structure
- **test_models.py**: Model creation and relationship testing
- **test_crud.py**: CRUD operation testing with async database sessions
- **test_api.py**: API endpoint testing with test client
- **conftest.py**: Test configuration with async database fixtures

### Test Database
- **Engine**: SQLite with aiosqlite for async testing
- **Isolation**: Each test gets a fresh database session
- **Fixtures**: Comprehensive fixtures for projects, requests, and artifacts

### Running Tests
```bash
# Run all tests
make test

# Run backend tests only  
make backend-test

# Run specific test file
cd apps/backend && poetry run pytest tests/test_models.py
```

## Data Types and Enums

### SourceKind
- `ddl`: SQL DDL schema definition
- `json`: JSON schema/configuration
- `introspection`: Database introspection

### RequestType  
- `relational`: Multi-table relational data
- `flat`: Single table/CSV data
- `timeseries`: Time-series data

### RequestStatus
- `pending`: Created but not started
- `running`: Currently processing
- `completed`: Successfully finished
- `failed`: Processing failed
- `cancelled`: Manually cancelled

### ArtifactFormat
- `csv`: Comma-separated values
- `xlsx`: Excel spreadsheet
- `parquet`: Apache Parquet
- `jsonl`: JSON Lines
 - `html`: Validation report (self-contained HTML)

## Error Handling

### API Error Responses
- **400 Bad Request**: Validation errors, duplicate resources
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server/database errors

### Validation
- **Pydantic Schemas**: Request/response validation with detailed error messages
- **Database Constraints**: Foreign key validation, unique constraints
- **Business Logic**: Custom validation (e.g., duplicate project names)

## Security Considerations

### API Keys
- **Hashed Storage**: API keys stored as SHA-256 hashes (peppered with `SECRET_KEY`)
- **Scoped Access**: Granular permission system via scopes array (`read:project`, `write:project`, `run:request`, `read:artifacts`)
- **Project Association**: Keys tied to specific projects

### OIDC
- **Verification**: Minimal JWKS-based ID token verification; full code flow can be added later
- **Dependency**: Uses `python-jose` when available; otherwise returns `501` for verification attempts

### Audit Trail
- **Comprehensive Logging**: All actions logged via AuditEvent model
- **Actor Tracking**: User identification for all operations
- **Project Context**: Actions linked to projects where applicable

## Performance Considerations

### Database Optimization
- **Indexes**: Strategic indexes on foreign keys and query columns
- **UUIDs**: Primary keys use UUIDs for distribution/security
- **JSONB**: Efficient JSON storage with query capabilities
- **Connection Pooling**: Async connection pool for scalability

### Query Optimization
- **Pagination**: Built-in pagination for list endpoints
- **Selective Loading**: Efficient relationship loading
- **Async Operations**: Non-blocking database operations

## Next Steps

### Generation Engine Integration
1. **Queue Integration**: Connect RQ (Redis Queue) for background processing
2. **Status Updates**: Implement request status transition workflow  
3. **Artifact Storage**: Integrate MinIO for file storage
4. **Progress Tracking**: Real-time progress updates

### API Enhancements
1. **Auth Flow**: Expand OIDC to full authorization code flow with refresh tokens
2. **Filtering**: Advanced filtering for list endpoints
3. **Webhooks**: Event notifications for request completion

### Monitoring & Observability
1. **Metrics**: Request processing metrics and performance tracking
2. **Logging**: Structured logging with correlation IDs
3. **Health Checks**: Comprehensive health checking for dependencies
4. **Alerting**: Error rate and performance alerting
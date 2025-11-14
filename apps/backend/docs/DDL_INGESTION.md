# DDL Ingestion Module

Comprehensive DDL ingestion system for parsing database schemas and building dependency graphs.

## Features

### 🔍 Multi-Dialect DDL Parsing
- **Supported Dialects**: PostgreSQL, MySQL, MS SQL Server, SAP HANA
- **Extraction**:
  - Tables and columns (name, data type, nullability)
  - Primary keys (including compound keys)
  - Unique constraints
  - Check constraints
  - Foreign key relationships
- **Automatic PII Detection**: Heuristic tagging of email, phone, name, address, etc.

### 📊 Schema Graph Analysis
- **DAG Construction**: Builds directed acyclic graph from foreign key relationships
- **Topological Sorting**: Determines proper data generation order
- **Cycle Detection**: Identifies circular dependencies
- **Junction Table Detection**: Automatically identifies many-to-many relationship tables
- **Dependency Analysis**:
  - Root tables (no dependencies)
  - Leaf tables (no dependents)
  - Table dependency levels
  - Generation order grouping for parallel processing

### 🌐 REST API Endpoints

#### Upload Source
```http
POST /api/v1/projects/{project_id}/sources
Content-Type: multipart/form-data

Parameters:
- file: DDL SQL file (.sql, .ddl) or schema JSON (.json)
- dialect: postgres | mysql | mssql | hana (for DDL files)
```

**Response:**
```json
{
  "source_id": "uuid",
  "schema_id": "uuid",
  "kind": "ddl",
  "tables_count": 15,
  "warnings": ["warning messages"]
}
```

#### List Sources
```http
GET /api/v1/projects/{project_id}/sources?skip=0&limit=50
```

Query Parameters:
- `skip` (int, default 0): Number of records to skip (offset pagination)
- `limit` (int, default 100): Max number of sources to return (cap enforced server-side)

Example Response:
```json
[
  {
    "id": "b5e3c6c2-3d6b-4f6e-9c1d-9f9d8c7e1a11",
    "project_id": "d3a12f0b-0a5f-4c9e-a2f1-2c0e5f8b1234",
    "kind": "ddl",
    "storage_uri": "file://.../b5e3c6c2_schema.sql",
    "checksum": "5d41402abc4b2a76b9719d911017c592",
    "created_at": "2025-11-10T12:34:56.789Z"
  }
]
```

Notes:
- Returns lightweight `Source` objects (without embedded schema). Use `GET /sources/{source_id}` for full schema.
- Future: cursor-based pagination & filtering by kind/checksum.

#### Get Schema
```http
GET /api/v1/projects/{project_id}/sources/{source_id}
```

**Response:**
```json
{
  "id": "uuid",
  "source_id": "uuid",
  "schema": {
    "tables": [
      {
        "name": "users",
        "columns": [
          {
            "name": "email",
            "dtype": "VARCHAR(255)",
            "nullable": false,
            "pii_tag": "EMAIL"
          }
        ],
        "pk": ["user_id"],
        "uniques": [["email"]],
        "checks": [],
        "fks": []
      }
    ],
    "dag": {
      "nodes": ["users", "orders"],
      "edges": [["orders", "users"]]
    },
    "warnings": []
  },
  "dag": {...},
  "warnings": [],
  "created_at": "2025-11-05T..."
}
```

#### Get DAG
```http
GET /api/v1/projects/{project_id}/sources/{source_id}/dag
```

#### Get Tables
```http
GET /api/v1/projects/{project_id}/sources/{source_id}/tables
```

## Canonical Schema Format

```json
{
  "tables": [
    {
      "name": "string",
      "columns": [
        {
          "name": "string",
          "dtype": "string",
          "nullable": boolean,
          "pii_tag": "string?"
        }
      ],
      "pk": ["column_names"],
      "uniques": [["column_names"]],
      "checks": [
        {
          "name": "string?",
          "expression": "string"
        }
      ],
      "fks": [
        {
          "from_col": "string",
          "to_table": "string",
          "to_col": "string"
        }
      ]
    }
  ],
  "dag": {
    "nodes": ["table_names"],
    "edges": [["from_table", "to_table"]]
  },
  "warnings": ["string"]
}
```

## Usage Examples

### Python API Usage

```python
from app.utils.ddl_parser import parse_ddl
from app.utils.schema_graph import (
    topological_sort,
    find_junction_tables,
    get_generation_order
)

# Parse DDL
with open("schema.sql") as f:
    ddl_content = f.read()

schema = parse_ddl(ddl_content, dialect="postgres")

# Analyze dependencies
sorted_tables, is_valid = topological_sort(schema.dag)
junction_tables = find_junction_tables(schema.tables)
generation_groups = get_generation_order(schema.dag)

print(f"Tables in generation order: {sorted_tables}")
print(f"Junction tables: {junction_tables}")
print(f"Generation groups for parallel processing: {generation_groups}")
```

### cURL Examples

#### Upload DDL File
```bash
curl -X POST "http://localhost:8000/api/v1/projects/{project_id}/sources" \
  -F "file=@ecommerce.sql" \
  -F "dialect=postgres"
```

#### Upload JSON Schema
```bash
curl -X POST "http://localhost:8000/api/v1/projects/{project_id}/sources" \
  -F "file=@schema.json"
```

#### Get Schema
```bash
curl "http://localhost:8000/api/v1/projects/{project_id}/sources/{source_id}"
```

## Testing

### Run Unit Tests
```bash
pytest tests/test_ddl_parser.py -v
```

### Run Integration Tests
```bash
pytest tests/test_sources_api.py -v
```

### Test with Sample Schema
```bash
# Use the provided sample ecommerce schema
pytest tests/test_ddl_parser.py::test_parse_postgres_ddl -v
```

## Data Type Normalization

The parser normalizes data types across different SQL dialects:

| Original | Normalized |
|----------|------------|
| INT, INTEGER, INT4, SERIAL | INTEGER |
| BIGINT, INT8, BIGSERIAL | BIGINT |
| VARCHAR(N), CHARACTER VARYING(N) | VARCHAR(N) |
| DECIMAL(P,S), NUMERIC(P,S) | DECIMAL(P,S) |
| TIMESTAMP WITH TIME ZONE | TIMESTAMP |
| BOOL, BOOLEAN, BIT | BOOLEAN |
| UUID, UNIQUEIDENTIFIER | UUID |

## PII Detection

Automatic heuristic PII tagging based on column names:

| Pattern | PII Tag |
|---------|---------|
| *email*, *e_mail* | EMAIL |
| *phone*, *mobile*, *tel* | PHONE |
| *first_name*, *last_name*, *full_name* | NAME |
| *address*, *street*, *city*, *postal*, *zip* | ADDRESS |
| *ssn*, *social_security*, *national_id* | IDENTIFIER |
| *credit_card*, *card_number* | PAYMENT |

## Architecture

```
┌─────────────────┐
│  FastAPI        │
│  Endpoint       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DDL Parser     │◄────── sqlglot
│  (ddl_parser.py)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Schema Graph    │
│ (schema_graph.py)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │
│  (Schema model) │
└─────────────────┘
```

## Files Structure

```
app/
├── utils/
│   ├── ddl_parser.py      # DDL parsing logic
│   └── schema_graph.py    # DAG analysis utilities
├── schemas/
│   └── schema.py          # Pydantic schemas
├── api/
│   └── api_v1/
│       └── endpoints/
│           └── sources.py # API endpoints
└── db/
    └── models.py          # Schema model

tests/
├── test_ddl_parser.py     # Parser unit tests
├── test_sources_api.py    # API integration tests
└── sample_schemas/
    └── ecommerce.sql      # Sample DDL file
```

## Migration

Run the migration to create the `schemas` table:

```bash
alembic upgrade head
```

Or apply manually if needed:
```bash
python apply_migration.py
```

## Future Enhancements

- [ ] Support for views and materialized views
- [ ] Index definition extraction
- [ ] Trigger and stored procedure parsing
- [ ] Column-level constraints (DEFAULT values)
- [ ] Enhanced PII detection with ML models
- [ ] Support for more SQL dialects (Oracle, DB2)
- [ ] Schema diff and versioning
- [ ] Visual DAG rendering
- [ ] Export to other formats (Terraform, Liquibase)

## License

Part of the Synthetic Data Platform project.

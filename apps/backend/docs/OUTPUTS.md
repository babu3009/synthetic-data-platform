# Outputs: Files, Postgres Upsert, and Kafka Events

This guide explains how to configure outputs for generation requests:

- File artifacts (CSV, Parquet, XLSX, JSONL) uploaded to MinIO or local storage
- Postgres write-back using batched, transaction-safe upserts
- Kafka event publishing with optional partition keys and headers

Use these options independently or together. All configuration lives under `params_json.outputs` on the Request resource.

## Prerequisites

- MinIO up and configured in `.env` (or local storage fallback enabled)
- Optional: a reachable PostgreSQL instance for DB write-back
- Optional: a reachable Kafka cluster for event publishing

## File Artifacts

When formats like CSV/Parquet/XLSX/JSONL are selected for a request, artifacts are written chunk-wise and uploaded under:

```
s3://<bucket>/requests/{requestId}/...
```

Artifacts are discoverable via:

- `GET /api/v1/requests/{request_id}/artifacts`

Note: File format selection is driven by the request creation payload (Wizard UI or API). See project README for end-to-end flow.

## Postgres Write-back (Upsert)

Enable database write-back to insert/update rows directly into your own Postgres tables while the generator runs.

Configuration (in `params_json.outputs.db`):

```json
{
  "outputs": {
    "db": {
      "enabled": true,
      "dsn": "postgresql+psycopg2://user:pass@host:5432/mydb",
      "table_map": {
        "customers": "public.customers",
        "orders": "public.orders"
      },
      "conflict_columns_map": {
        "customers": ["id"],
        "orders": ["id"]
      },
      "batch_size": 10000
    }
  }
}
```

Supported fields:

- `enabled` (bool): Turn DB write-back on/off
- `dsn` (string): Sync SQLAlchemy DSN; use `+psycopg2` driver
- `table_map` (object): Map generator table names to fully-qualified DB tables
- `table_prefix` (string, optional): Prefix to prepend when `table_map` is not provided per table
- `conflict_columns_map` (object): Map table names to the `ON CONFLICT (...) DO UPDATE` columns
- `batch_size` (int, optional, default 10,000): Rows per batched insert

Behavior:

- Rows are inserted using `INSERT ... ON CONFLICT (...) DO UPDATE`
- Batches are wrapped in a single transaction per request
- If `conflict_columns_map[table]` is omitted, primary key columns are used when discoverable

### Minimal curl example (create request with DB upsert)

```bash
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/requests/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "relational",
    "seed": 42,
    "params_json": {
      "rows": 100000,
      "tables": ["customers", "orders"],
      "outputs": {
        "db": {
          "enabled": true,
          "dsn": "postgresql+psycopg2://postgres:postgres@localhost:5432/synthetic_data_platform",
          "table_map": {"customers": "public.customers", "orders": "public.orders"},
          "conflict_columns_map": {"customers": ["id"], "orders": ["id"]}
        }
      }
    }
  }'
```

## Kafka Event Publishing

Publish each generated row as a JSON event to a Kafka topic.

Configuration (in `params_json.outputs.kafka`):

```json
{
  "outputs": {
    "kafka": {
      "enabled": true,
      "brokers": ["localhost:9092"],
      "topic": "synthetic-events",
      "key_field": "id",
      "headers": {"source": "synth"},
      "linger_ms": 20,
      "batch_size": 32768,
      "acks": "all",
      "include_table_name": true
    }
  }
}
```

Supported fields:

- `enabled` (bool): Turn Kafka publishing on/off
- `brokers` (array|string): Broker list (e.g., `"host:9092"` or `["host1:9092","host2:9092"]`)
- `topic` (string): Target topic
- `key_field` (string, optional): Column whose value is used as the message key
- `headers` (object, optional): String headers attached to each message
- `linger_ms`, `batch_size`, `acks` (optional): Producer tuning
- `include_table_name` (bool, optional): If true, add `__table__` to payload

Events are serialized as JSON objects. If `key_field` is provided, the producer uses it to set the partition key.

### Minimal curl example (create request with Kafka publishing)

```bash
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/requests/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "relational",
    "seed": 7,
    "params_json": {
      "rows": 5000,
      "tables": ["customers"],
      "outputs": {
        "kafka": {
          "enabled": true,
          "brokers": ["localhost:9092"],
          "topic": "synthetic-events",
          "key_field": "id",
          "include_table_name": true
        }
      }
    }
  }'
```

## Estimates Before Running

You can request a fast estimate of rows/size/time for a request before starting it:

```bash
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/requests/${REQUEST_ID}:estimate"
```

The response includes rough per-table and total estimates. The estimator is heuristic and may vary by engine and configuration.

## Operational Notes & Troubleshooting

- Ensure target tables exist and your `dsn` user has `INSERT/UPDATE` permissions.
- Use `+psycopg2` in the DSN for write-back (the upsert path uses a synchronous engine under the hood).
- If Kafka is unreachable, the job will surface producer errors; check broker addresses, firewall rules, and topic existence.
- MinIO credentials and bucket configuration are managed by the backend environment; see `ENVIRONMENT.md`.

## See Also

- Root README: Outputs overview and Wizard flow
- `BACKEND_DATABASE.md`: API endpoints for requests and artifacts
- `QUICK_REFERENCE.md`: Handy commands and quick links

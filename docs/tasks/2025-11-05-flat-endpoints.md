# Flat data generation API: preview and start (RQ background)

Date: 2025-11-05

## What was added

- Implemented `flat` API router with:
  - POST `/api/v1/flat/preview`: returns the first 100 rows for a given flat schema by invoking `app.services.flat.preview`.
- Implemented request-scoped start action:
  - POST `/api/v1/requests/{request_id}:start`: enqueues an RQ job to generate artifacts for `flat` requests. The worker writes chunked files via `app.services.flat.generate_to_artifacts` and uploads using the storage abstraction (MinIO if available, otherwise local storage). The RQ `job_id` is stored under `Request.params_json.job_id`.

## Files changed/added

- `app/api/api_v1/endpoints/flat.py`
  - `router` with `/preview` endpoint.
  - `req_router` with `/{request_id}:start` endpoint that enqueues RQ job and persists `job_id` in `params_json`.
  - Worker handles persistence of artifacts and stats and all status transitions.
- `app/api/api_v1/api.py`
  - Registered routers: `flat.router` under `/flat` and `flat.req_router` under `/requests`.
- `app/core/rq.py`
  - Helper to create a Redis connection and default RQ `Queue` from settings.
- `app/jobs/flat_job.py`
  - RQ worker job that updates `Request` status PENDING -> RUNNING -> COMPLETED (or FAILED on error), writes artifacts and stats, and persists them.

## Behavior details

- Preview endpoint expects a JSON payload with the flat schema structure:
  - `{ "fields": [{ "name": str, "provider": {...}, "null_prob"?: float, "unique"?: bool }], "seed"?: int }`
  - Returns the first 100 rows deterministically based on `seed`.
- Start action now enqueues a background job and returns immediately with the updated `Request` (including `params_json.job_id`).
  - The worker reads `schema/config`, `rows`, `formats`, and `chunk_size` from `Request.params_json`, writes chunked files to a temp folder, uploads them, and records `Artifact` rows.
  - Supported formats: csv, jsonl, parquet, xlsx.
  - Per-column statistics are computed and stored under `params_json.stats` by the worker.

## Notes

- MinIO is used when configured; otherwise local storage under `storage/requests/` is used with file URIs and self-signed URLs.
- To process jobs, run an RQ worker with the same environment (e.g., `rq worker -u redis://<host>:<port>/<db> default`).

## Next steps

- Add API to check job status and error handling for failures.
- Add tests for preview determinism and 100k-row generation performance and memory limits.
- Wire artifact download URLs in API responses if needed.

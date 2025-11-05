# Frontend ↔ Backend integration notes (2025-11-06)

This page captures quick, practical notes so we can wire the UI later with minimal discovery.

## Base URL
- API prefix: `/api/v1`
- Ensure CORS allows the frontend dev origin (e.g., `http://localhost:5173` or `http://localhost:3000`).

## Key endpoints

- Flat preview
  - POST `/api/v1/flat/preview`
  - Body: flat schema config (JSON)
  - Returns: first 100 rows (array of records)

- Create a request
  - POST `/api/v1/projects/{project_id}/requests/`
  - Body (example): `{ "type": "relational" | "flat" | "timeseries", "seed": 123, "params_json": { ... } }`
  - Returns: Request JSON `{ id, project_id, type, status='pending', seed, params_json, ... }`

- Start request (background job)
  - POST `/api/v1/requests/{request_id}:start`
  - Behavior: enqueues an RQ job based on request type (flat or relational)
  - Side effects: `params_json.job_id` is set; status transitions will be updated by the worker

- Poll request status / get request
  - GET `/api/v1/projects/{project_id}/requests/{request_id}`
  - Returns updated status `pending|running|completed|failed` and updated `params_json`, including `relational_report` when available

- List artifacts for a request
  - GET `/api/v1/requests/{request_id}/artifacts`
  - Returns: array of artifacts `{ id, format: 'csv'|'xlsx'|'parquet'|'jsonl', storage_uri, size_bytes, created_at }`

- On-demand validation (no persistence)
  - POST `/api/v1/validate`
  - Body:
    ```json
    {
      "rules": [
        {"when": "orders.total > 1000", "then": ["orders.channel in ['WEB','PARTNER']"]},
        {"uniqueness": ["customers.email"]},
        {"distribution": {"product.category": {"A": 0.5, "B": 0.3, "C": 0.2}}},
        {"temporal": "shipment.promised_date <= shipment.order_date + 2d"}
      ],
      "data_sample": {"orders": [{"id":1, "total": 1500, "channel":"WEB"}]},
      "data_final":  {"orders": [{"id":2, "total": 1200, "channel":"STORE"}]},
      "max_violations": 10
    }
    ```
  - Response:
    ```json
    {
      "rules": [ /* normalized rules */ ],
      "report": {
        "sample": [ /* per-rule results */ ],
        "final": [ /* per-rule results */ ]
      }
    }
    ```

## Types (frontend)

- Rules (normalized)
  ```ts
  type Rule =
    | { type: 'implication'; table: string; when: string; then: string[] }
    | { type: 'uniqueness'; table: string; columns: string[] }
    | { type: 'distribution'; table: string; column: string; probs: Record<string, number> }
    | { type: 'temporal'; table: string; left: string; op: '<='|'<'|'>='|'>'|'=='|'!='; right: { column: string; offset_days: number } };
  ```

- Validation report (simplified)
  ```ts
  type RuleResult = {
    type: string;
    table: string;
    checked?: number;
    violations?: number;
    violation_rate?: number;
    samples?: any[];
    stat?: { n: number; chi2: number; df: number; critical: number; pass: boolean };
    observed?: Record<string, number>;
  };

  type ValidationReport = { sample: RuleResult[]; final: RuleResult[] };
  ```

- Request, Artifact
  ```ts
  type Request = {
    id: string;
    project_id: string;
    type: 'relational'|'flat'|'timeseries';
    status: 'pending'|'running'|'completed'|'failed'|'cancelled';
    seed?: number;
    params_json?: any; // includes job_id, relational_report (when available)
    created_at: string;
    started_at?: string;
    finished_at?: string;
  };

  type Artifact = {
    id: string;
    request_id: string;
    format: 'csv'|'xlsx'|'parquet'|'jsonl';
    storage_uri: string;
    size_bytes: number;
    created_at: string;
  };
  ```

## Fetch helpers (sketch)

```ts
async function validateRules(body: any, base = '/api/v1') {
  const r = await fetch(`${base}/validate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ rules: Rule[]; report: ValidationReport }>;
}

async function createRequest(projectId: string, payload: Partial<Request>, base = '/api/v1') {
  const r = await fetch(`${base}/projects/${projectId}/requests/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Request>;
}

async function startRequest(requestId: string, base = '/api/v1') {
  const r = await fetch(`${base}/requests/${requestId}:start`, { method: 'POST' });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Request>; // refreshed request
}

async function getRequest(projectId: string, requestId: string, base = '/api/v1') {
  const r = await fetch(`${base}/projects/${projectId}/requests/${requestId}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Request>;
}

async function listArtifacts(requestId: string, base = '/api/v1') {
  const r = await fetch(`${base}/requests/${requestId}/artifacts`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<Artifact[]>;
}
```

## UI wiring plan

- Validate Rules page
  - Textareas/editors for DSL JSON, sample JSON, final JSON
  - Submit → call `/api/validate`; render per-rule results: checked, violations, rate, and for distribution show chi2/pass/observed; show a small table of samples for violations

- Start Generation flow
  - Create request → Start → Poll status every 2s via GET request until `completed|failed`
  - On `completed`, fetch artifacts list and show download links; if `relational`, display `params_json.relational_report` (FK coverage + collisions)

## Error handling
- Show backend `detail` string on HTTP 400/404
- For long-running jobs, surface `params_json.error` if present after failure

## Notes
- XLSX is a single workbook shared across tables (multi-sheet) for relational generation
- `relational_report` is under `params_json.relational_report`
- CORS: ensure FastAPI includes dev origin for smooth local testing

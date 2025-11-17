# 🚀 Quick Reference - Conda Environment

## Environment: `conda-synthetic-data`

### Activation
```powershell
conda activate conda-synthetic-data
```

### Deactivation
```

### Check Status
```powershell
# List all environments (active has *)
conda info --envs

# Check active environment
echo $env:CONDA_DEFAULT_ENV
```

### Package Management
```powershell
# List installed packages
conda list
pip list

# Install new package
pip install <package-name>

# Update package
pip install --upgrade <package-name>

# Export environment
conda env export > environment.yml
pip freeze > requirements.txt
```

### VS Code
- **Reload Window**: `Ctrl+Shift+P` → "Developer: Reload Window"
- **Select Interpreter**: `Ctrl+Shift+P` → "Python: Select Interpreter"
- Current: `Python 3.11.14 ('conda-synthetic-data')`

### Environment files
- Local: copy `apps/backend/.env.example` to `.env` and edit values.
- Production: use `apps/backend/.env.prod.example` as a hardened template; inject real secrets via a vault.

### Development Commands
```powershell
# Activate first!
conda activate conda-synthetic-data

# Navigate to backend
cd C:\Code\python\synthetic-data-platform\apps\backend

# Run validation
python validate_implementation.py

# Run tests
pytest

# Start server
uvicorn app.main:app --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "message"

# Seed database
python -m app.scripts.seed_db
```

### Helper Scripts
```powershell
# From apps/backend directory
.\activate-conda.ps1
```

### Troubleshooting
```powershell
# If imports fail
conda activate conda-synthetic-data
pip install --force-reinstall <package-name>

# If VS Code doesn't detect
# 1. Reload window: Ctrl+Shift+P → Reload
# 2. Select interpreter: Ctrl+Shift+P → Select Interpreter

# Check Python path
python -c "import sys; print(sys.executable)"
# Should show: C:\pyenv\.conda\envs\conda-synthetic-data\python.exe
```

### Environment Details
- **Python**: 3.11.14
- **Location**: `C:\pyenv\.conda\envs\conda-synthetic-data\`
- **Conda**: `C:\ProgramData\miniforge3\`
- **Packages**: 34 installed

### Key Packages
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.121.0 | Web framework |
| uvicorn | 0.38.0 | ASGI server |
| sqlalchemy | 2.0.44 | Database ORM |
| alembic | 1.17.1 | Migrations |
| pydantic | 2.12.4 | Validation |
| pytest | 8.4.2 | Testing |

### Documentation
- `ENVIRONMENT.md` - Complete environment guide
- `CONDA_MIGRATION_COMPLETE.md` - Setup summary
- `ENVIRONMENT_SETUP_COMPLETE.md` - Detailed docs

---
**Status**: ✅ Ready for Development

### Additional Docs
- `OUTPUTS.md` - File artifacts, Postgres upsert, Kafka publishing (config and examples)
 - HTML Report - See `OUTPUTS.md` (HTML validation report section)
 - Providers Inference - See README_DATABASE.md (Providers & PII section)
 - LLM Admin & Settings - See README_DATABASE.md (LLM Administration & Project LLM Settings)
 - Frontend LLM Settings UI implemented: project-level toggle, provider/model selection, advanced params (temperature/top_p/max_tokens), guardrails (block PII, allow tool use), and test suggestions panel calling `/api/v1/projects/{projectId}/infer/providers`.
 - Backend validation: `PUT /api/v1/projects/{projectId}/llm-settings` enforces `model_id` belongs to `provider_id` (422 on mismatch).
 - Rate limiting: `POST /api/v1/projects/{projectId}/infer/providers` capped at 60/min per project → 429 + audit `llm.infer.rate_limited` when exceeded.
 - Rate limiting: `POST /api/v1/projects/{projectId}/infer/providers` capped at `INFER_RATE_LIMIT_PER_MINUTE` (env, default 60) per project → 429 + optional audit `llm.infer.rate_limited` (flag `FF_ENABLE_RATE_LIMIT_AUDIT`).
 - Probe auditing: `POST /api/v1/admin/llm/providers/{providerId}:probe` now emits `llm.provider.probe` audit event (flag `FF_ENABLE_PROBE_AUDIT`) including success/disabled state.
 - See `docs/TRACING_RATE_LIMIT.md` for consolidated tracing + rate limit configuration guidance.

### Quick Links
- Outputs configuration: see `apps/backend/docs/OUTPUTS.md`
- Requests API (estimate/start): see `docs/BACKEND_DATABASE.md`
 - Metrics endpoint: `GET http://localhost:8000/metrics`
 - Tracing: set `OTEL_EXPORTER_OTLP_ENDPOINT` in backend env
	- Provider suggestions: `POST /api/v1/projects/{projectId}/infer/providers` or `/api/v1/infer/providers`
 - LLM Admin (OWNER): `GET/POST/PATCH /api/v1/admin/llm/providers?project_id=...`;
	 `POST /api/v1/admin/llm/providers/{providerId}/credentials?project_id=...`;
	 `GET/POST /api/v1/admin/llm/providers/{providerId}/models?project_id=...`;
	 `POST /api/v1/admin/llm/providers/{providerId}:probe?project_id=...`;
	 `POST /api/v1/admin/llm/providers/{providerId}:discover-models?project_id=...`
 - Project LLM Settings: `GET/PUT /api/v1/projects/{projectId}/llm-settings`
	 - Frontend page route: `/projects/{projectId}/llm-settings` (OWNER/EDITOR editable; VIEWER read-only)

### LLM quick examples

```powershell
# Create an LLM provider (OWNER role; note the project_id query param for RBAC scope)
curl -X POST "http://localhost:8000/api/v1/admin/llm/providers?project_id=${PROJECT_ID}" `
	-H "Content-Type: application/json" `
	-d '{
		"kind": "openai",
		"name": "openai",
		"base_url": "https://api.openai.com/v1",
		"is_enabled": true
	}'

# Upsert provider credentials (server encrypts at rest; masked in audit logs)
curl -X POST "http://localhost:8000/api/v1/admin/llm/providers/${PROVIDER_ID}/credentials?project_id=${PROJECT_ID}" `
	-H "Content-Type: application/json" `
	-d '{
		"api_key": "sk-...",
		"org_id": null,
		"extra": {}
	}'

# Discover and upsert provider models (returns diff summary)
curl -X POST "http://localhost:8000/api/v1/admin/llm/providers/${PROVIDER_ID}:discover-models?project_id=${PROJECT_ID}" `
    -H "Content-Type: application/json"

# Update project-level LLM settings (EDITOR+)
curl -X PUT "http://localhost:8000/api/v1/projects/${PROJECT_ID}/llm-settings" `
	-H "Content-Type: application/json" `
	-d '{
		"enabled": true,
		"provider_id": "${PROVIDER_ID}",
		"model_id": "${MODEL_ID}",
		"temperature": 0.2,
		"top_p": 1.0,
		"max_tokens": 512
	}'
```

Validation errors examples (HTTP 422):
```json
{"detail":"model_id requires provider_id"}
```
```json
{"detail":"model_id does not belong to provider_id"}
```
```

### Providers inference (quick)

```powershell
# Infer per-column providers (heuristic-only example)
curl -X POST "http://localhost:8000/api/v1/projects/${PROJECT_ID}/infer/providers" `
	-H "Content-Type: application/json" `
	-d '{
		"columns": [
			{"table": "customers", "column": "email", "dtype": "text", "description": "customer email"},
			{"table": "customers", "column": "first_name", "dtype": "text"}
		],
		"llm": {"enabled": false}
	}'
```

Rate limit response (HTTP 429) (configurable via `INFER_RATE_LIMIT_PER_MINUTE`):
```json
{"detail":"Rate limit exceeded; try again later"}
```

Response shape (per column suggestions):

```json
{
	"results": [
		{
			"table": "customers",
			"column": "email",
			"suggestions": [
				{
					"provider_config": "email",
					"score": 0.98,
					"source": "heuristic",
					"provider": "email",
					"reasons": ["column looks like email"],
					"pii": {"tag": "contact.email"}
				}
			]
		}
	]
}
```

Tracing & Metrics:
```powershell
# Enable OpenTelemetry tracing (OTLP HTTP)
#set in .env
ENABLE_TRACING=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=synthetic-data-backend

# Metrics endpoint (always on if ENABLE_METRICS=true)
curl http://localhost:8000/metrics
```

Adjust rate limit:
```powershell
# Example override to 120 requests per minute
INFER_RATE_LIMIT_PER_MINUTE=120
FF_ENABLE_RATE_LIMIT_AUDIT=true
```

Notes:
- If project LLM settings are enabled and a client resolves, an extra `source: "LLM"` suggestion may appear; ranking sorts by score desc and prefers LLM on ties.
- For a deeper walkthrough and save examples, see `README_DATABASE.md` → Providers & PII.

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
# Should show: C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\python.exe
```

### Environment Details
- **Python**: 3.11.14
- **Location**: `C:\Users\Isaiyavan Karan\.conda\envs\conda-synthetic-data\`
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

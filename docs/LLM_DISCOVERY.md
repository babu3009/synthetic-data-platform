# LLM Provider & Model Discovery

This guide covers the administrative LLM endpoints for managing providers, credentials, probing connectivity, and discovering models. All routes under `/api/v1/admin/llm` require:

- `project_id` query parameter
- The caller to have OWNER role in the referenced project
- Auth header (e.g. Bearer token) for your principal

## Endpoint Summary

| Operation | Method & Path | Notes |
|-----------|---------------|-------|
| List providers | GET `/api/v1/admin/llm/providers?project_id=<uuid>` | Returns all registered providers. |
| Create provider | POST `/api/v1/admin/llm/providers?project_id=<uuid>` | Body: `kind`, `name`, optional `base_url`. Name must be unique. |
| Update provider | PATCH `/api/v1/admin/llm/providers/{provider_id}?project_id=<uuid>` | Toggle `is_enabled`, change base URL, etc. |
| Upsert credentials | POST `/api/v1/admin/llm/providers/{provider_id}/credentials?project_id=<uuid>` | Body: `api_key`, optional `org_id`, `extra` JSON. Encrypted at rest. |
| List models | GET `/api/v1/admin/llm/providers/{provider_id}/models?project_id=<uuid>` | Existing models in DB. |
| Create model (manual) | POST `/api/v1/admin/llm/providers/{provider_id}/models?project_id=<uuid>` | Manual definition; fields include `name`, `display_name`, `context_tokens`, `supports_json`, `is_default`. |
| Probe provider | POST `/api/v1/admin/llm/providers/{provider_id}:probe?project_id=<uuid>` | Lightweight connectivity & credential check. Returns `ok` & `message`. Audited if feature flag enabled. |
| Discover models | POST `/api/v1/admin/llm/providers/{provider_id}:discover-models?project_id=<uuid>` | Fetches remote model list for supported kinds, upserts, assigns default if none. |

Supported `kind` values: `openai`, `anthropic`, `ollama`, `lmstudio`, `custom` (custom has no built‑in discovery/probe logic).

## Typical Workflow
1. Create provider (or ensure it exists).
2. Upsert credentials (for OpenAI / Anthropic; Ollama & LM Studio are local and usually need only a base URL).
3. Probe to validate connectivity & credentials.
4. Discover models to populate / update the catalog (auto-assigns a default model if none exists yet).
5. Optionally manually patch provider or add custom models.

## Curl Examples
Assumptions:
- API base: `http://localhost:8000`
- Auth token saved in `$TOKEN`
- Project UUID in `$PROJECT_ID`

### 1. Create OpenAI Provider
```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"openai","name":"openai-main"}'
```

### 2. Upsert Credentials
```bash
OPENAI_PROVIDER_ID=<uuid returned above>
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers/$OPENAI_PROVIDER_ID/credentials?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"sk-live-REDACT","org_id":null,"extra":{}}'
```
Response contains `masked_api_key` (never returns plaintext).

### 3. Probe Provider
```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers/$OPENAI_PROVIDER_ID:probe?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN"
# => {"ok":true,"message":"openai ok; latency_ms=..."}
```

If missing credentials: `{"ok":false,"message":"missing credentials; latency_ms=..."}`

### 4. Discover Models (OpenAI)
```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers/$OPENAI_PROVIDER_ID:discover-models?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" > /tmp/openai_models.json
jq '.added_count,.updated_count,.unchanged_count' /tmp/openai_models.json
```

### 5. Ollama Provider + Discovery
Create local provider (no credentials needed if default URL `http://localhost:11434`):
```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"ollama","name":"ollama-local"}'
OLLAMA_PROVIDER_ID=<uuid>
```

Discover models:
```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers/$OLLAMA_PROVIDER_ID:discover-models?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.models[].name'
```

### 6. LM Studio Provider
```bash
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"lmstudio","name":"lmstudio-local","base_url":"http://localhost:1234"}'
LMSTUDIO_PROVIDER_ID=<uuid>
curl -s -X POST "http://localhost:8000/api/v1/admin/llm/providers/$LMSTUDIO_PROVIDER_ID:discover-models?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.models | length'
```

## Discovery Behavior
- Each discover run fetches remote metadata and upserts into DB.
- Fields compared for updates: `display_name`, `context_tokens`, `supports_json`, `metadata_json`.
- Counts returned: `added_count`, `updated_count`, `unchanged_count`.
- Default assignment: If provider has no default model yet, the first discovered model is marked `is_default=true` and others remain false.

## Probe Behavior
`probe` performs a minimal GET request against provider-specific model listing endpoints with a short timeout (3s).

Provider heuristics:
- OpenAI: GET `/v1/models` with `Authorization: Bearer <api_key>`.
- Anthropic: GET `/v1/models` with `x-api-key` header.
- Ollama: GET `/api/tags` (local CLI API).
- LM Studio: GET `/v1/models` (local LM Studio API).

Common messages:
| Message prefix | Meaning |
|----------------|---------|
| `openai ok` / `anthropic ok` / `ollama ok` / `lmstudio ok` | Success |
| `missing credentials` | API key required but not found |
| `unauthorized` | API key invalid / revoked |
| `timeout` | Endpoint unreachable within probe timeout |
| `provider disabled` | `is_enabled` is false |
| `exception:` | Unexpected error (network, parse, etc.) |

Latency (ms) appended in final message for quick health tracking.

## Troubleshooting
| Symptom | Cause | Resolution |
|---------|-------|-----------|
| `missing credentials` on probe or 0 models discovered | Credentials not stored | Upsert credentials, re-run probe/discover |
| `unauthorized` | Invalid or expired API key | Rotate key, update credentials |
| Empty `models` array after discovery | Insufficient permissions / bad base URL | Verify base URL & key; check provider API docs |
| `timeout` | Network/firewall or wrong port | Confirm service reachable locally (e.g. `curl <base_url>/v1/models`) |
| Default model not set | First discovery failed to persist or no models | Re-run discovery; check audit log `llm.model.discover` |

## Audit Events
Actions logged (when feature flags like `FF_ENABLE_PROBE_AUDIT` are ON):
- `llm.provider.create`, `llm.provider.update`
- `llm.credential.upsert`
- `llm.model.create`, `llm.model.discover`
- `llm.provider.probe`

Include counts for discovery and latency for probe.

## Security & Storage
- API keys encrypted at rest (payload sealed before DB write).
- Returned credential object contains only `masked_api_key`.
- Model metadata persisted in `metadata_json` for downstream UI (e.g. capabilities, version info).

## Related
- Project-level LLM settings & guardrails: see frontend LLM Settings page and `ProjectLLMSetting*` schemas.
- Tracing & rate limits: `docs/TRACING_RATE_LIMIT.md`.

### Python import guidance (for internal integrations)

When programmatically constructing LLM clients from backend code, prefer the modular factory:

```python
from app.modules.llm.factory import LLMClientFactory

client = LLMClientFactory.for_project(db, project_id)
```

Legacy re-exports remain under `app/services/llm/` for backward compatibility during the deprecation window.

## Next Steps
After successful discovery:
1. Set project LLM settings (`provider_id` + `model_id` + optional temperature/top_p/max_tokens).
2. Enable guardrails or JSON mode depending on provider capabilities.
3. Use inference or provider suggestion endpoints with confirmed configuration.

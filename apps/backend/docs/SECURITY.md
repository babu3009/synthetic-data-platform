# Security: Authentication, API Keys, and RBAC

This backend supports two authentication modes and fine-grained authorization:

- OIDC (OpenID Connect) login for end-users (frontend flow)
- Project-scoped API keys for service-to-service access
- Role-based access control (RBAC) for users per project

## OIDC (OpenID Connect)

Configure via environment variables in `apps/backend/.env` (see `.env.example` for defaults):

- `SECRET_KEY` – Required. Server-side secret used as pepper for hashing API keys and other security features. Set a strong value in all environments.

- `OIDC_ISSUER` – Provider issuer URL
- `OIDC_CLIENT_ID` – Client ID
- `OIDC_CLIENT_SECRET` – Client secret
- `OIDC_REDIRECT_URI` – Callback URL (e.g., http://localhost:8000/api/v1/auth/callback)
- `OIDC_SCOPES` – Space-separated list (default: `openid profile email`)

Endpoints:
- `GET /api/v1/auth/login` – Returns an authorize URL for the frontend to redirect users
- `GET /api/v1/auth/callback` – Scaffolded: accepts an `id_token` param and verifies it using JWKS if present

Notes:
- Full auth code flow (exchanging `code` for tokens) can be added later. The current scaffolding verifies an ID token when provided.
- Verified users are represented as principals with `kind="user"` and `user_sub=<subject>`.
- OIDC token verification uses `python-jose` when available. If it is not installed, verification attempts will return `501 Not Implemented` (tests and non-OIDC flows still work).

## API Keys

Project-scoped API keys allow non-interactive access with scopes:

- `read:project` – Read project details and list project resources
- `write:project` – Create/update project-scoped resources (e.g., requests)
- `run:request` – Start background jobs for a request
- `read:artifacts` – Read artifacts and get signed URLs

Headers:
- Keys are sent via `X-API-Key: <plaintext>`

Key Management Endpoints (OWNER only):
- `GET /api/v1/projects/{project_id}/api-keys/` – List keys (hashed only)
- `POST /api/v1/projects/{project_id}/api-keys/` – Create a key; returns plaintext once
- `DELETE /api/v1/projects/{project_id}/api-keys/{key_id}` – Revoke key

Storage:
- Only a SHA-256 hash of the API key is stored (with `SECRET_KEY` as pepper).
- Audit events are emitted on create/revoke: `api_key.create`, `api_key.revoke`.

## RBAC (Users)

Users (from OIDC `sub`) are members of projects with a role:

- `OWNER` – Full control, can manage API keys and members
- `EDITOR` – Can modify project resources and run requests
- `VIEWER` – Read-only access to project and artifacts

Implementation:
- Model: `ProjectMember` with fields `(project_id, user_sub, role)`
- Authorization checks use `require_project_scope` to combine user role and API key scopes

## Authorization Model

A request is authorized if either condition is met:
- API Key: The key’s `project_id` matches and the key includes the required scopes
- User: The user is a `ProjectMember` with a role that meets or exceeds the required role(s)

Examples:
- Read project: `read:project` OR role in {VIEWER, EDITOR, OWNER}
- Update project: `write:project` OR role in {EDITOR, OWNER}
- Run request: `run:request` OR role in {EDITOR, OWNER}
- Read artifacts: `read:artifacts` OR role in {VIEWER, EDITOR, OWNER}

## LLM Admin Access (OWNER)

LLM administration endpoints require OWNER role. These routes use a project-scoped query parameter to establish RBAC context:

- Example: `GET /api/v1/admin/llm/providers?project_id={project_id}`

All mutations emit audit events with sensitive values masked (e.g., secret payloads replaced by placeholders). Credentials are write-only and never returned in responses.

## LLM Credentials Encryption

Provider credentials are encrypted at rest and never stored in plaintext. The server accepts a structured payload like:

```json
{
	"api_key": "***",
	"org_id": "...",
	"extra": {"region": "us-east-1"}
}
```

- At write-time, the payload is encrypted and stored in `llm_credentials.enc_payload_json`.
- At read-time, responses include only a masked value (e.g., `masked_api_key` shows last 4 chars); the full secret is never returned.
- Audit events record masked values only.

Key management:
- Local development/production: set `LLM_SECRET_KEY` to a strong secret; if it is not a Fernet key, the service derives one from it.
- Optional Azure Key Vault: set `KEY_VAULT_URL` and `KEY_VAULT_SECRET_NAME` to fetch the encryption key from Key Vault. If Key Vault is unreachable, the service falls back to `LLM_SECRET_KEY`.

Implementation notes:
- Preferred cipher is Fernet (cryptography library). If `cryptography` is not installed, a clearly marked, weak fallback is used for dev/test. For secure deployments, ensure `cryptography` is installed and `LLM_SECRET_KEY` (or Key Vault) is configured.

## Testing

- Use `X-User-Sub: <sub>` header to simulate an authenticated user in tests.
- Create API keys via the management endpoints and pass them via `X-API-Key`.
- See `tests/test_auth_api_keys.py` for scope and role coverage.

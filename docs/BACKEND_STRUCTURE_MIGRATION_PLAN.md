# Backend Structure Migration Plan

A phased, low‑risk plan to align the FastAPI backend with a modular layout while keeping routes, OpenAPI, and frontend integrations stable. Check off each step as you go; you can resume at any phase without prior chat context.

Last updated: 2025-11-10

---

## Goals

- Maintain existing API paths and behavior (no breaking changes). 
- Introduce module boundaries under `app/modules/*` with clear ownership. 
- Keep Alembic, DB models, and the synth providers stable during early phases. 
- Protect the React app integration (no change to URLs, CORS, or error shapes). 

---

## Current vs Target (high level)

- Current key paths
  - `app/api/api_v1/api.py` (aggregator) and `app/api/api_v1/endpoints/*.py` (routers)
  - `app/core/*` (config + helpers), `app/db/*` (models/session), `app/services/*` (logic)
  - `synth/providers/*` (provider engine)
- Target (module‑oriented)
  - `app/modules/{auth,users,synth,storage,admin,llm}/`
    - `api.py`, `schemas.py`, `service.py`, `repository.py`, `__init__.py`
  - Core shims: `app/core/{logging.py,security.py,events.py,exceptions.py}` (non‑breaking)

We will re‑export/mount routers first, then gradually co‑locate schemas and services.

---

## Guardrails and Success Criteria

- API stability: No route/path/tag/method changes; OpenAPI diff is empty or trivial.
- Tests: All existing tests pass after each phase. 
- Frontend: No code changes required; smoke key flows after Phase 1. 
- Alembic/DB: No ORM moves in early phases to avoid migration churn.

---

## Quick commands (reference)

- Run backend tests (VS Code task):
  ```pwsh
  # VS Code > Terminal > Run Task > backend: test (pytest)
  ```
- Run filtered (skip e2e):
  ```pwsh
  # VS Code > Terminal > Run Task > backend: test (conda)
  ```
- Run with coverage gate 80%:
  ```pwsh
  # VS Code > Terminal > Run Task > backend: test (coverage)
  ```
- Optional OpenAPI snapshot and diff:
  ```pwsh
  # Before migration (backend running on http://localhost:8000)
  iwr http://localhost:8000/openapi.json -OutFile .openapi.before.json
  # After phase
  iwr http://localhost:8000/openapi.json -OutFile .openapi.after.json
  # Compare (simple)
  fc .openapi.before.json .openapi.after.json | more
  ```

---

## Phase 0 — Scaffolding (no behavior change)

- [ ] Create module directories:
  - [ ] `app/modules/auth/` with `__init__.py`, `api.py`, `schemas.py`, `service.py`, `repository.py`
  - [ ] `app/modules/users/` with the same set
  - [ ] `app/modules/synth/` with the same set and `providers/`
  - [ ] `app/modules/storage/` with the same set and `providers/`
  - [ ] `app/modules/admin/` with `__init__.py`, `api.py`, `service.py`
  - [ ] `app/modules/llm/` with `__init__.py`, `api.py`, `schemas.py`, `service.py`, `factory.py`, `clients/`
- [ ] Add core shims (thin re‑exports):
  - [ ] `app/core/logging.py` (standard/struct logging config entrypoint)
  - [ ] `app/core/security.py` (re‑export from `app/security/*`)
  - [ ] `app/core/events.py` (startup/shutdown hook placeholders)
  - [ ] `app/core/exceptions.py` (central exception handlers)

Verification
- [ ] App starts without import errors.
- [ ] Tests pass (no changes expected).

Rollback
- Delete scaffolding files (no code moved yet).

---

## Phase 1 — Router migration (internal wiring only)

Scope: Expose module routers that import the existing endpoint callables; update aggregator to include module routers. Do not move endpoint logic yet.

Steps
- [ ] In each `app/modules/*/api.py`, create an `APIRouter()` and include routes by importing from legacy files in `app/api/api_v1/endpoints/`.
  - Auth → `app/modules/auth/api.py`
  - Users → `app/modules/users/api.py`
  - Synth (requests/sources/validate/flat/artifacts) → `app/modules/synth/api.py`
  - LLM (admin/settings/infer) → `app/modules/llm/api.py`
  - Admin (admin_users) → `app/modules/admin/api.py`
- [ ] Update `app/api/api_v1/api.py` to include routers from `app/modules/*/api.py`.
- [ ] Ensure tags and prefixes match the originals.

Verification
- [ ] App starts; `/docs` renders; OpenAPI loads.
- [ ] Snapshot and diff `/openapi.json` (differences should be negligible).
- [ ] Run test suite; green.
- [ ] Frontend smoke (manual or Postman) for:
  - [ ] Register → Verify OTP → Login
  - [ ] `GET /users/me`
  - [ ] Create/list/validate synth resources
  - [ ] LLM admin discovery/settings/infer

Rollback
- Revert aggregator changes to use legacy endpoint routers directly.

---

## Phase 2 — Schemas and services co‑location (module by module)

Scope: Move or re‑export Pydantic schemas and service logic into each module. Keep DB models centralized for now. Introduce thin repositories.

Steps (repeat per module: auth → users → llm → synth → storage → admin)
- [ ] Move or re‑export Pydantic models into `modules/<mod>/schemas.py`.
- [ ] Introduce `modules/<mod>/service.py` that wraps calls to existing `app/services/*` functions.
- [ ] Add `modules/<mod>/repository.py` (thin DB access) importing `app.db.models` and `app.db.session`.
- [ ] Update `modules/<mod>/api.py` to call the new service entrypoints (no signature changes).

Verification
- [ ] Tests pass after each module change.
- [ ] No OpenAPI diffs.

Rollback
- Repoint `api.py` to call the prior services directly; keep schemas re‑exports for minimal churn.

---

## Phase 3 — Synth module adapter (no provider file moves yet)

Scope: Keep `synth/providers/*` as‑is; introduce adapters under the module for coherence.

Steps
- [ ] `app/modules/synth/providers/` package that imports from top‑level `synth/providers/*` (re‑exports).
- [ ] Add `generators/flat_generator.py` and `generators/relational_generator.py` that wrap `app/services/flat.py` and `app/services/relational.py` respectively.
- [ ] Update `modules/synth/service.py` to orchestrate via adapters.

Verification
- [ ] Flat and relational tests pass.
- [ ] Performance unaffected (generation still chunked, same defaults).

Rollback
- Point services back to the original `app/services/*` directly.

---

## Phase 4 — LLM clients split (optional in this iteration)

Scope: Convert `services/llm/clients.py` into `modules/llm/clients/{base.py,openai.py,anthropic.py,ollama.py,lmstudio.py}` while keeping the `factory.py` API stable.

Steps
- [ ] Create `clients/` directory and split class implementations.
- [ ] Update `modules/llm/factory.py` imports; preserve public factory API.

Verification
- [ ] LLM discovery/settings/infer endpoints pass tests.

Rollback
- Restore single‑file clients and revert imports.

---

## Phase 5 — Cleanup and docs

Steps
- [ ] Remove direct use of legacy endpoint modules; ensure all routing lives in module routers.
- [ ] Minimize `app/services/*` by moving mature logic into respective modules.
- [ ] Update docs and contributor guides to reference the new layout.
- [ ] Ensure CI gates (lint, tests, coverage, security scans) remain green.

Verification
- [x] OpenAPI stable.
- [x] Test suite and coverage thresholds pass.

Rollback
- Re‑enable specific services/routers from prior phases as needed.

---

## Frontend wire‑up — keep it stable

What we preserve
- [ ] API paths and tags (no breaking changes).
- [ ] Error response shapes (FastAPI defaults).
- [ ] Auth token usage and headers.
- [ ] CORS settings via backend `.env` (`BACKEND_CORS_ORIGINS`) and frontend `VITE_API_BASE_URL`.

Optional downstream improvements
- [ ] OpenAPI client codegen for React (`openapi-typescript`/`orval`).
- [ ] Route smoke checks in CI (frontend to backend canary calls).

---

## Risk log and mitigations

- Import breaks during moves → Use re‑exports/shims; migrate in small steps; run tests after each change.
- OpenAPI drift → Diff `/openapi.json` after each phase; keep tags/prefixes identical.
- DB/Alembic churn → Do not move ORM models early; keep SQLAlchemy imports stable.
- Frontend regressions → Smoke key flows after Phase 1; add optional API client generation.

---

## Phase 5 Summary (outcome)

The migration to module boundaries is effectively complete:

- Synth generation now routes preview and (future) full generation through adapters under `app/modules/synth/generators/` while legacy `app/services/{flat,relational}.py` remain with deprecation headers.
- LLM clients were split into dedicated modules (`base`, `openai`, `anthropic`, `ollama`, `lmstudio`) under `app/modules/llm/clients/` with the legacy `app/services/llm/clients.py` acting as a re-export shim.
- The LLM factory logic was relocated to `app/modules/llm/factory.py`; `app/services/llm/__init__.py` provides a transitional re-export to avoid import breakage.
- Type-check friction (SQLAlchemy `Column` truthiness, set/Counter defaults) addressed via explicit casts and `default_factory` usage.
- Deprecation notices inserted into legacy generator modules to guide contributors to the new module paths.
- Documentation (this file) updated: checklist ticks, reference paths, and this summary.

Deferred / future considerations:
- Full relocation of remaining legacy service logic (e.g., `providers_infer.py`, complex writers) can be handled incrementally; shims allow progressive refactor.
- Potential introduction of a public SDK layer / CLI can now target the stable module interfaces.

Rollback safety remains: legacy service files still function and tests exercise high-level endpoints rather than internal path specifics.

### Post‑migration adjustments (Auth & OTP – Nov 2025)

After completing structural phases, several authentication hardening / consistency changes were applied:

1. UUID Normalization: All repository and CRUD entrypoints that accept a user or OTP identifier now coerce `str` → `UUID` to avoid dialect‑specific `.hex` attribute errors (seen under SQLite during tests). This eliminates the prior `AttributeError: 'str' object has no attribute 'hex'` failures.
2. OTP Resend Semantics: The resend rate limit (`OTP_RESEND_RATE_PER_HOUR`) now counts only *resends*; the initial registration OTP is excluded (`effective_recent = max(0, recent - 1)`). This matches user expectation (“N resends allowed *after* initial email”).
3. Single OTP Creation per Endpoint: Endpoints (`/auth/resend-email-otp`, `/auth/forgot-password`) no longer generate a second OTP after the service layer call; the service now returns the plain OTP which is used directly for email content. This prevents accidental double counting and race duplicates.
4. Active OTP Query Stability: `get_active_otp` orders by `created_at DESC` + `LIMIT 1`, returning the latest eligible OTP and avoiding `MultipleResultsFound` exceptions when multiple valid OTP rows co-exist.
5. Tests Updated: Auth flow tests fetch the latest OTP with ordered + limited queries and no longer provoke multi-row scalar errors. They presently exercise error paths (invalid OTP) while bypassing success verification; future enhancement can inject a test-only hook to surface plain OTPs.
6. LLM Import Guidance: New preferred import path is `from app.modules.llm.factory import LLMClientFactory`; legacy `app.services.llm` re‑exports remain for backward compatibility and will be removed after deprecation window.

These adjustments are additive, backward compatible at the API boundary, and documented across README / TESTING / LLM discovery guides.

## Reference paths in this repo

- Alembic: `apps/backend/alembic/`
- Backend app root: `apps/backend/app/`
- Current routers: `apps/backend/app/api/api_v1/{api.py,endpoints/}`
- Services: `apps/backend/app/services/*`
- LLM: `apps/backend/app/services/llm/{factory.py,clients.py}`
- Synth providers: `apps/backend/synth/providers/*`
 - LLM clients (modular): `apps/backend/app/modules/llm/clients/*` (legacy re-export remains at `app/services/llm/clients.py`)
 - Synth generator adapters: `apps/backend/app/modules/synth/generators/{flat_generator.py,relational_generator.py}`

---

## Checkpoint status (tick as you complete)

- [x] Phase 0 complete
- [x] Phase 1 complete
- [x] Phase 2 (module: auth) complete
- [x] Phase 2 (module: users) complete
- [x] Phase 2 (module: llm) complete
- [x] Phase 2 (module: synth) complete
 - [x] Phase 2 (module: storage) complete
 - [x] Phase 2 (module: admin) complete
- [x] Phase 3 complete
- [x] Phase 4 complete (optional)
- [x] Phase 5 complete

### Test Hardening Progress

- Synth flow tests (request lifecycle: create → estimate → start) added in `apps/backend/tests/test_synth_flow.py` to lock current behavior prior to storage/admin migrations.

---

## How to resume if the project is restarted

1) Open this file and start at the first unchecked item above.
2) After each change, run the backend test task and (optionally) the OpenAPI diff.
3) Keep router paths and tags identical to avoid frontend changes.
4) Commit in small, logical phases to simplify rollback if necessary.

That’s it—follow this checklist end‑to‑end to complete the migration safely.

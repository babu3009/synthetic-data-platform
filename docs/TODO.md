# Project TODOs

This document captures planned enhancements, grouped by area, to pick up after the current instructions are complete.

## Frontend

- [x] ERD diagram UI
  - Replace Diagram tab placeholder with an interactive ERD: render tables and PK/FK edges, pan/zoom, auto-layout, and drag for manual positioning. Persist layout per entity.
- [ ] Per-project wizard routing
  - Change Wizard route to `/wizard/:projectId` instead of query param. Update links and load entities by route param.
- [ ] Dev auth headers toggle
  - In `services/sources.ts`, add an optional dev-mode toggle to send `X-User-Sub` or `X-API-Key` headers for local testing. Make configurable via env or local storage.
- [ ] Wizard state unit tests
  - Add tests for reducer actions: setProject, addEntity, setSelectedEntity, setActiveTab; uniqueness helper; canonical schema mapping. Use Jest/Vitest.
- [ ] Sources service tests
  - Mock axios and test `uploadDDLSource`, `uploadJSONSource`, `getSourceSchema` including fallback from `/sources/{id}` to `/tables`. Verify headers and form-data usage.
- [ ] Entities page integration test
  - Render `EntitiesPage` with provider; simulate Add Entity modal flows (DDL/JSON/Fields); assert entity added, selected, and tab switches to Diagram.
- [ ] UX and validation polish
  - Improve loading/disabled states, inline API error banners, and success hints. Enforce table name uniqueness and per-table column name uniqueness. Disable Create while parsing/validating.
- [ ] Import/export entity schema UI
  - Allow exporting entity schema to JSON and importing from JSON (merge or replace). Provide download and upload UI in Entities tab.
- [ ] Role-based UI controls
  - Use RBAC (OWNER/EDITOR/VIEWER) to hide/disable mutation actions (create/edit/delete). Respect scopes when API keys are used.
- [ ] Canonical types and validation
  - Add strict TypeScript types (or zod schemas) for canonical schema JSON. Validate pasted JSON client-side before sending to backend.
- [ ] Project picker in wizard
  - Add a project selector in the Wizard header to switch projects; reload entities accordingly. Persist last selection.
- [ ] Autosave fields designer
  - Autosave unfinished designer state (Fields tab) to local storage and restore on reopen. Provide reset/clear action.
- [ ] Performance scaling
  - Handle large schemas: virtualize entity tables list, debounce expensive operations, and guard parse/validate size limits.
- [ ] Telemetry emission for flows
  - Emit analytics events for entity creation flows (DDL/JSON/Fields), parse success/fail, and common errors for UX tuning.
- [ ] Auth hardening frontend
  - Integrate real OIDC flow in frontend; avoid long-lived tokens in localStorage (consider memory storage or cookie approach).
- [ ] Frontend entities API client
  - Once backend entities endpoints exist, add a typed client for CRUD and wire listing, creation, updates, and deletion.
- [ ] Wizard docs and screenshots
  - Document Wizard usage (DDL/JSON/Fields), include screenshots/gifs, and add troubleshooting notes to the frontend README.
- [ ] CI: frontend pipeline
  - Add CI to lint, type-check, build, and run tests for the frontend. Cache node_modules for speed; report coverage.

### Admin → LLM & Project LLM Settings

- [x] Admin LLM Providers page (OWNER only)
  - List providers, toggle enable, manage credentials (view-only for non-OWNER), discover models, and probe.
- [x] React Query hooks and services for admin endpoints
  - Providers CRUD, credentials upsert, models list/create, probe, and discover-models.
- [x] File naming policy
  - Converted component files to snake_case; PascalCase re-export stubs remain for now.
- [ ] Remove PascalCase re-export stubs
  - Physically delete `ProviderFormModal.tsx`, `CredentialsModal.tsx`, `DiscoverDrawer.tsx` when safe (Windows case-collision handled).
- [x] Project → LLM Settings page (OWNER/EDITOR editable)
  - Enable toggle, provider and model selects (filtered to enabled), advanced tuning (temperature/top_p/max_tokens), guardrails (PII block, tool use), Test Suggestion panel.
- [ ] Manual smoke test
  - Run frontend locally and verify: settings load/save, role-based disables, provider/model filtering, and Test Suggestion results.
- [ ] LLM Settings page tests (advanced)
  - Add coverage for advanced params persistence (temperature/top_p/max_tokens) and guardrails toggles; assert payloads on save.
- [ ] Manual smoke test
  - Run frontend locally and verify: settings load/save, role-based disables, provider/model filtering, and Test Suggestion results.


#### Backend Enhancements (recently added)
- [x] Provider/model ownership validation
  - Server-side check in PUT `/api/v1/projects/{projectId}/llm-settings` ensures `model_id` belongs to `provider_id`; returns 422 otherwise.
- [x] Per-project inference rate limit
  - Added in-memory limiter (60/min) for `POST /api/v1/projects/{projectId}/infer/providers` with 429 and audit `llm.infer.rate_limited`.
- [x] Audit probe events
  - Emit audit event for provider probe (`llm.provider.probe`) to complete coverage.
- [x] Assert audit in rate limit tests
  - Extend test to verify `llm.infer.rate_limited` audit row insertion.

- [ ] Rules tab persistence
  - Persist Rules per entity (localStorage + backend endpoints). Prefer backend when available; define typed schema.
- [ ] Rules & Providers tests
  - Add unit/integration tests for Providers & PII grid (edits, auto-suggest, save) and Rules editor (YAML/JSON sync, lints, dry-run validate).
- [ ] Wizard quick-start docs
  - Add a brief quick-start to the frontend README for the Wizard (Entities, Diagram, Providers & PII, Rules), with screenshots/GIFs.
- [ ] Fast-refresh cleanup
  - Extract navbar to `components/navbar.tsx`, reintroduce `app.tsx`, and remove no-op placeholders to clear Vite fast-refresh warning.

### Outputs & Run

- [x] Outputs & Run tab UI
  - Formats, destination, optional schedule, estimate call, and create/start request flow; navigation to Request Detail.
- [x] Request Detail page
  - Poll status until terminal state and list/download artifacts; link from Outputs & Run.

## Backend

- [ ] Persist entities server-side
  - Add backend endpoints to create/read/update/delete EntitySchemas. Save Wizard-created entities to the database; fetch on Wizard load; ensure name uniqueness per project enforced server-side.
- [ ] More SQL dialect support
  - Extend DDL parsing dialect options (e.g., MSSQL, Oracle) and optionally auto-detect dialect from content.
- [ ] Backend create-from-canonical
  - Add a dedicated backend endpoint to accept canonical schema JSON and create an EntitySchema atomically. Return created entity with ID.
- [ ] Entities import/export endpoints
  - Implement endpoints to export an EntitySchema to JSON and to import canonical JSON into a persisted EntitySchema. Handle validation and deduplication.
- [ ] Telemetry ingestion and storage
  - Add backend endpoints or logging to accept telemetry events from the frontend and store/aggregate them for UX analysis.

### LLM Client & Adapters

- [ ] Integration tests
  - Add tests that decrypt credentials and exercise factory with mocked HTTP across adapters; include negative cases (disabled provider, bad key).
- [x] Model discovery endpoints
  - Implemented real `:discover-models` for OpenAI, Anthropic, Ollama, LM Studio with per-provider parsing, upsert, diff summary, and audit logging.
  - Follow-ups below extend tests and robustness.
- [x] Infer/providers ranking & gating
  - Designed response schema to return per-column `suggestions[]` with `provider_config`, `score`, `source`, `provider`, `reasons`, and `pii`.
  - Implemented combined inference: heuristic baseline plus optional LLM-refined suggestion; ranking now sorts by score desc and prefers LLM on ties.
  - Wired LLM gating via `ProjectLLMSetting` + `LLMClientFactory`; if disabled or misconfigured, heuristic-only path is used.
  - Updated and added tests: adjusted existing infer tests and added `tests/api/test_infer_providers_llm.py` mocking adapters across provider kinds; verified disabled behavior.
  - Test run green for infer/providers and existing suites.
- [ ] Scoring logic upgrade
  - Replace heuristic `suggest_providers` ranking with prompt- or rule-based scoring that considers data types, PII tags, and context window. Add tunables.
- [ ] Local-first preference toggle
  - Add config to prefer local adapters (Ollama/LM Studio) when reachable; otherwise fall back to remote providers.
- [ ] Multi-credential selection
  - Support multiple credentials per provider and selection policy (by project, by tag/region, round-robin).
- [ ] Caching and rate-limit guards
  - Cache probe/model lists per provider and respect provider-specific rate limits. Add circuit-breaker behavior on repeated failures.
- [ ] Integration tests
  - Add tests that decrypt credentials and exercise factory with mocked HTTP across adapters; include negative cases (disabled provider, bad key).
  
#### New Follow-ups (Post Discovery Implementation)
- [ ] Discovery tests (Anthropic & LM Studio)
  - Add unit tests mirroring OpenAI/Ollama coverage for Anthropic and LM Studio discovery parsing and diff counters.
- [ ] Error taxonomy & logging
  - Standardize exceptions for network, auth, rate-limit, and schema parsing; surface structured error codes in probe/discover responses.
- [ ] Error taxonomy & logging
  - Standardize exceptions for network, auth, rate-limit, and schema parsing; surface structured error codes in probe/discover responses.
- [ ] Default model policy
  - Add periodic task or admin action to re-evaluate `is_default` per provider when context windows or recommended base models change.
- [ ] Caching layer
  - Cache raw discovery payloads (short TTL) to reduce repeated external calls when multiple admins trigger discovery.

#### Testing Additions
- [x] Invalid model/provider tests
  - Added test covering missing `provider_id` and mismatched provider/model (422) and valid pairing (200).
- [x] Rate limit tests
  - Added test confirming 60 successful inference calls then 429 on exceed within same minute window.
- [ ] Docs expansion
  - Extend QUICK_REFERENCE and ENVIRONMENT docs with discovery usage examples (curl), default assignment rules, and troubleshooting (e.g., missing API key).

- [ ] Providers save endpoint
  - Implement/confirm `PUT /api/v1/projects/{project_id}/entities/{entity_id}/providers` and align with frontend contract.
- [ ] Validate endpoint
  - Ensure `/api/v1/validate` exists and returns compact ValidationReport matching frontend contract; add tests.
- [ ] Lifespan migration
  - Replace `@app.on_event` startup/shutdown with lifespan context manager and adjust tests/DI accordingly.
- [ ] Pydantic shadowing fix
  - Resolve SchemaResponse field shadowing warnings and add a regression test.

### Requests lifecycle

- [x] Implement estimate route
  - `POST /api/v1/projects/{project_id}/requests/{request_id}:estimate` returns `{rows,size_bytes,seconds}` (fields optional by engine).
- [ ] Implement start route
  - `POST /api/v1/requests/{request_id}:start` transitions status from `pending` to `running` and enqueues processing.

### Documentation

- [x] Add curl examples for Providers, Validate, and Requests lifecycle
  - Update backend docs with examples for infer/save providers, validate, create/estimate/start requests, status, and artifacts.

- [ ] Outputs documentation (DB/Kafka)
  - Create `apps/backend/docs/OUTPUTS.md` with configuration and curl examples; add links from root README and backend docs.

---

This list mirrors the in-editor task tracker and can be maintained alongside code reviews and milestones.

## ✅ Done

- [x] Add navbar link to LLM Settings and LLM Providers (project-scoped when URL contains projectId)
  - Commit: a697cc3a
  - Added links in `src/main.tsx` with auto-detected projectId from path; includes fallbacks when absent.
- [x] LLM Settings page tests (base)
  - Commit: a697cc3a
  - Added tests for role gating (VIEWER disables), model filtering per provider, Test Suggestion panel wiring, and Save submission payload.
- [x] Tracing & rate-limit docs
  - Commit: a697cc3a
  - Created `TRACING_RATE_LIMIT.md`, linked from backend docs and root, and referenced settings/env toggles.
- [x] Connectivity probes (real) and probe endpoint real call
  - Commit: a697cc3a
  - Implemented provider-specific lightweight probes (OpenAI/Anthropic/Ollama/LM Studio) with timeout, latency_ms in audit, and error classification.
- [x] Fix discover-models provider_id NOT NULL bug
  - Commit: a697cc3a
  - Ensure models and credentials are created with provider_id set pre-commit; adjusted tests accordingly.

## Recently Completed

- [x] Autosave & dirty-nav guard
  - Added 800ms autosave for Diagram and Providers tabs, tracked dirty flag, and warned on navigating away with unsaved changes.
- [x] Draft mode for entities
  - Autosaved partial entities per project and rehydrated them on load so users can leave and return later.
 - [x] Accessibility (A11y) improvements
   - Added keyboard navigation for diagram node lists (Space/Enter toggles PK, E opens editor, Arrow keys navigate) and Providers grid (Alt+ArrowUp/Down to move vertically). Added aria-labels and visible focus outlines aligned with Bootstrap.
 - [x] Tooltips and inline help
   - Added contextual tooltips for PK/FK indicators, row targets (absolute/ratioTo), distribution field help, and Providers grid headers (Provider, Config, PII).
 - [x] Dark mode compatibility
   - Implemented prefers-color-scheme dark styles and Bootstrap-friendly focus rings without introducing a new CSS framework.
 - [x] Performance optimizations
   - Windowed long column lists in diagram table nodes (paged view) and lazy-loaded the Column Editor modal to reduce initial bundle size.

  - [x] Postgres upsert writer (backend)
    - Batched `INSERT ... ON CONFLICT DO UPDATE` with single-transaction safety; configurable `table_map`, `conflict_columns_map`, and `batch_size`.
  - [x] Kafka event writer (backend)
    - JSON publishing with optional `key_field`, headers, and producer tuning; optional `include_table_name` flag.
  - [x] Outputs wiring for generators/jobs
    - Relational and flat generators write to file artifacts and optionally DB/Kafka; jobs pass `params_json.outputs.*` configs.
  - [x] Estimate endpoint
    - `POST /api/v1/projects/{project_id}/requests/{id}:estimate` implemented with heuristic estimator service.
  - [x] E2E MinIO upload test
    - Generates large relational datasets and uploads CSV/Parquet to MinIO; skips gracefully when MinIO isn’t configured.
  - [x] README updates
    - Root README documents Outputs (files/DB/Kafka) and estimate endpoint; cross-links to backend docs.

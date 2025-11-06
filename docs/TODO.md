# Project TODOs

This document captures planned enhancements, grouped by area, to pick up after the current instructions are complete.

## Frontend

- [ ] ERD diagram UI
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

- [ ] Rules tab persistence
  - Persist Rules per entity (localStorage + backend endpoints). Prefer backend when available; define typed schema.
- [ ] Rules & Providers tests
  - Add unit/integration tests for Providers & PII grid (edits, auto-suggest, save) and Rules editor (YAML/JSON sync, lints, dry-run validate).
- [ ] Wizard quick-start docs
  - Add a brief quick-start to the frontend README for the Wizard (Entities, Diagram, Providers & PII, Rules), with screenshots/GIFs.
- [ ] Fast-refresh cleanup
  - Extract navbar to `components/navbar.tsx`, reintroduce `app.tsx`, and remove no-op placeholders to clear Vite fast-refresh warning.

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

- [ ] Providers save endpoint
  - Implement/confirm `PUT /api/v1/projects/{project_id}/entities/{entity_id}/providers` and align with frontend contract.
- [ ] Validate endpoint
  - Ensure `/api/v1/validate` exists and returns compact ValidationReport matching frontend contract; add tests.
- [ ] Lifespan migration
  - Replace `@app.on_event` startup/shutdown with lifespan context manager and adjust tests/DI accordingly.
- [ ] Pydantic shadowing fix
  - Resolve SchemaResponse field shadowing warnings and add a regression test.

---

This list mirrors the in-editor task tracker and can be maintained alongside code reviews and milestones.

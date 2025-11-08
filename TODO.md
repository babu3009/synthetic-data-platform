# TODO

## Open
- [ ] P0: Add backend periodic artifact cleanup test
  - Paths: apps/backend/app/jobs/cleanup.py; apps/backend/tests/test_cleanup_task.py (new)
  - Description: Ensure `cleanup_expired_artifacts` and periodic scheduler logic work (single run + cancel on shutdown) without relying on real storage.
  - Acceptance Criteria:
    - Unit test mocks storage layer and asserts expired artifacts are removed.
    - Lifespan startup creates task; test verifies cancellation on shutdown via injecting short interval.

 - [x] P0: Add opt-in backend e2e CI job
  - Paths: .github/workflows/ci.yml
  - Description: Separate `backend-e2e` job (manual dispatch + nightly schedule) running `pytest -m e2e` with infra docker-compose spin-up.
  - Acceptance Criteria:
    - Job appears in workflow runs when manually dispatched.
    - Nightly schedule triggers job; PR runs unaffected.
    - Uses `-m e2e` and reports results; documented in TESTING.md.
  - Notes: Implemented via `backend-e2e` job with `workflow_dispatch` and nightly cron.

 - [x] P1: Frontend wizard project selection e2e test
  - Paths: apps/frontend/src/tests/e2e/project_wizard_flow.test.tsx (new)
  - Description: Validate project selection leads to `/projects/:projectId/wizard` route and essential wizard components render.
  - Acceptance Criteria:
    - Test passes; asserts route, presence of key tabs/components, and no MSW unhandled warnings.

 - [x] P1: Frontend flakiness heuristic script
  - Paths: apps/frontend/scripts/check-flakiness.mjs; .github/workflows/ci.yml
  - Description: Detect intermittent failures (retry-able patterns) and emit a single GitHub Actions warning annotation.
  - Acceptance Criteria:
    - Script parses Vitest output; raises annotation when heuristic threshold > N occurrences.
    - Can be disabled via env var `FLAKINESS_CHECK=0`.

- [x] P2: Enforce coverage thresholds (backend + frontend)
  - Paths: .github/workflows/ci.yml; apps/frontend/vitest.config.ts; TESTING.md
  - Description: Enforce coverage in CI with thresholds and upload reports to Codecov.
  - Acceptance Criteria:
    - Backend: `--cov-fail-under=80` in CI, coverage.xml uploaded.
    - Frontend: Vitest coverage thresholds configured; lcov uploaded.

- [x] P2: Investigate schema model field alias need
  - Paths: apps/backend/app/schemas/schema.py
  - Description: Confirm whether any Pydantic shadowing warnings remain; if so, introduce `Field(alias="schema")` or rename internal attribute while keeping wire format stable.
  - Acceptance Criteria:
    - No shadowing warnings after change.
    - JSON response field names unchanged for clients.

## Backlog (triaged)
- [ ] P2: Historical flakiness trend tracking (defer)
  - Paths: .github/workflows/ci.yml; scripts/flakiness-trend.ts
  - Description: Persist prior run stats (artifact or external store) to surface regressions over time.
  - Acceptance Criteria:
    - Optional job collects and publishes trend summary.
    - Not required for PRs.

- [ ] P3: Makefile coverage targets (optional)
  - Paths: Makefile
  - Description: Add `backend-coverage`, `frontend-coverage`, `coverage-all` to mirror CI coverage locally.
  - Acceptance Criteria:
    - Local `make` targets run coverage commands and produce reports.

## ✅ Done
- [x] 2025-11-07: PowerShell progress + converter + Pester + CI job — <commit>; summary: Added `ProgressTools` module, converter wrapper, Pester tests, and CI job.
- [x] 2025-11-07: Establish root TODO.md — <commit>; summary: Created root `TODO.md` baseline.
- [x] 2025-11-07: LLM Settings advanced tests — <commit>; summary: Added tests for advanced params & guardrails toggles.
- [x] 2025-11-07: Navbar project selector — <commit>; summary: Project picker modal and link interception for missing projectId.
- [x] 2025-11-07: LLM discovery docs — <commit>; summary: Added `docs/LLM_DISCOVERY.md` with provider examples.
- [x] 2025-11-07: Tighten PowerShell CI job — <commit>; summary: Hardened CI; added branch triggers.
- [x] 2025-11-07: Anthropic & LM Studio discovery tests — <commit>; summary: Added discovery parsing tests.
- [x] 2025-11-08: Remove Tailwind & standardize Bootstrap — <commit>; summary: Simplified PostCSS config; ensured only Bootstrap 5.x is used.
- [x] 2025-11-08: Per-project wizard routing — <commit>; summary: Implemented `/projects/:projectId/wizard` route + legacy redirect + tests.
- [x] 2025-11-08: Backend tests non-interactive & notify script — <commit>; summary: Added `scripts/run_backend_tests_notify.ps1` and `backend-test-notify` Makefile target; verified full pytest pass.
- [x] 2025-11-08: Introduce MSW baseline handlers — <commit>; summary: Added `handlers.ts` and server wiring; health handlers added.
- [x] 2025-11-08: FastAPI lifespan migration — <commit>; summary: Replaced deprecated on_event with lifespan context.
- [x] 2025-11-08: HTTP 422 constant update — <commit>; summary: Switched to HTTP_422_UNPROCESSABLE_CONTENT in LLM settings endpoint.
- [x] 2025-11-08: CI skip e2e by default — <commit>; summary: Added `-m "not e2e"` to backend-quality pytest command.
 - [x] 2025-11-08: Opt-in backend e2e CI job — <commit>; summary: Added `backend-e2e` job with manual + nightly triggers.
 - [x] 2025-11-08: Backend periodic artifact cleanup test — <commit>; summary: Added unit test for TTL logic & storage failure handling.
 - [x] 2025-11-08: Frontend project→wizard e2e — <commit>; summary: Added test to open selector, choose project, navigate, and assert wizard tabs.
 - [x] 2025-11-08: Frontend flakiness heuristic — <commit>; summary: Added Vitest JSON parsing script and CI integration with warning annotation.
 - [x] 2025-11-08: Backend Docker test target — <commit>; summary: Added `backend-test-docker` Make target and `Dockerfile.test`.
 - [x] 2025-11-08: MSW /health handler expansion — <commit>; summary: Added explicit `/health` handlers removing unhandled warnings.
 - [x] 2025-11-08: Backend test documentation consolidation — <commit>; summary: Added `TESTING.md` sections (Conda/Poetry/Notify/Docker) and README references.
 - [x] 2025-11-08: Register pytest e2e mark — <commit>; summary: Added `markers` entry in `pyproject.toml` to silence UnknownMark warning.
 - [x] 2025-11-08: Enforce coverage thresholds — <commit>; summary: Backend cov-fail-under=80, Vitest coverage thresholds + Codecov uploads; TESTING.md updated.
 - [x] 2025-11-08: Resolve Pydantic schema shadowing — <commit>; summary: Aliased SchemaResponse.schema via internal field and alias to remove warning.

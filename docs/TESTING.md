# Unified Testing Guide

This document consolidates all testing instructions for the Synthetic Data Platform across backend and frontend.

## Overview

Test Areas:
- **Backend**: FastAPI / Python / pytest (`apps/backend/tests`)
- **Frontend**: React / Vite / Vitest (`apps/frontend/src/tests`)
- **PowerShell / Scripts**: Pester tests under `testing/pwsh`

## Backend Testing

### 1. Conda Environment (Windows Recommended)
```powershell
conda activate conda-synthetic-data
cd apps/backend
pytest -q
```

### 2. Poetry Workflow
```powershell
make backend-setup   # install deps
make backend-test    # run pytest
```

### 3. Notification Wrapper
Long-running test runs can notify you when done:
```powershell
make backend-test-notify
# or
pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_tests_notify.ps1 -EnvName conda-synthetic-data -PytestArgs "-q"
```

### 4. Docker (Optional / Isolation)
```powershell
make backend-test-docker
```
Mount for iterative local development:
```powershell
docker run --rm -v ${PWD}/apps/backend:/app synthetic-data-platform/backend-test poetry run pytest -q
```

### Pytest Marks
- `e2e` — End-to-end tests (opt-in CI job). Skipped by default in quality pipeline via `-m "not e2e"`.

### Backend E2E (Opt-In CI Job)
Run locally:
```powershell
cd apps/backend
pytest -m e2e -q
```
CI triggers nightly (02:00 UTC) or manual dispatch and spins up infra via `docker compose` under `infra/`.

### Historical Warnings (Resolved)
- FastAPI `on_event` deprecation → migrated to lifespan.
- HTTP 422 constant → using `HTTP_422_UNPROCESSABLE_CONTENT`.

## Frontend Testing

Install & run:
```powershell
cd apps/frontend
pnpm install
pnpm test
```

Uses MSW handlers in `src/tests/mocks/handlers.ts`. Override per test as needed.

### Adding Tests
```tsx
// Example pattern
import { render, screen } from '@testing-library/react'
import MyComponent from '../components/my_component'

test('renders greeting', () => {
  render(<MyComponent />)
  expect(screen.getByText(/hello/i)).toBeInTheDocument()
})
```

### Network Mock Example
```ts
import { server } from './mocks/server'
import { rest } from 'msw'
server.use(rest.get('/api/v1/example', (_req, res, ctx) => res(ctx.status(200), ctx.json({ value: 42 }))))
```

## Combined Test Run
```powershell
make test
```
(Runs backend then frontend tests.)

## Coverage

### Backend Coverage (CI Threshold 80%)
CI command:
```powershell
pytest -m "not e2e" --cov=app --cov-report=xml --cov-fail-under=80
```
Local:
```powershell
cd apps/backend
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### Frontend Coverage (Vitest v8 provider)
Configured in `vitest.config.ts`:
```
lines: 80, functions: 80, branches: 70, statements: 80
```
Local:
```powershell
cd apps/frontend
pnpm vitest run --coverage
```
LCOV: `apps/frontend/coverage/lcov.info` (uploaded in CI).

### Make Targets
```powershell
make backend-coverage
make frontend-coverage
make coverage-all
```

## Flakiness Detection (Frontend)
- Script: `apps/frontend/scripts/check-flakiness.mjs`
- Consumes `vitest-report.json` (JSON reporter output). Emits a single GitHub Actions warning when heuristic threshold exceeded.
- Disable via `FLAKINESS_CHECK=0` env var.

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|-----------|
| PytestUnknownMarkWarning | Mark unregistered | Register `e2e` in pytest config or `conftest.py`. |
| MSW unhandled request | Missing handler | Add explicit handler or override in test. |
| Slow backend tests | External services / heavy data | Narrow with `-k`, use Docker isolation, or profile. |
| Deprecated act warning | Legacy Testing Library behavior | Upgrade `@testing-library/react` & avoid manual ReactDOMTestUtils.act. |

## Roadmap / Deferred
- Historical flakiness trend tracking (store JSON summaries as artifacts for regression insights).

---
Last updated: 2025-11-08 (consolidated)
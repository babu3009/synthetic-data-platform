# Testing Guide (Relocated)

The unified testing guide now lives at `docs/TESTING.md`.

Please refer to that file for current instructions on running backend, frontend, coverage, flakiness detection, and troubleshooting.

This legacy file is retained as a pointer to avoid broken references.

## Backend Testing

### 1. Conda Environment (Recommended for Windows)

If you have the `conda-synthetic-data` environment available:

```powershell
# Activate env
conda activate conda-synthetic-data
# Run backend tests
cd apps/backend
pytest -q
```

### 2. Poetry

If you prefer Poetry (ensures dependencies match `pyproject.toml`):

```powershell
make backend-setup   # installs deps via Poetry
make backend-test    # runs pytest
```

### 3. Notify Wrapper (Audible / Toast Notification)

Use the PowerShell wrapper to be notified when a long test run finishes:

```powershell
make backend-test-notify
# or direct
pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend_tests_notify.ps1
```

Parameters (optional):
```powershell
pwsh -File .\scripts\run_backend_tests_notify.ps1 -EnvName my-alt-env -PytestArgs "-q -k fast"
```

If the [BurntToast](https://github.com/Windos/BurntToast) module is installed you get a Windows toast; otherwise a console beep is used.

### 4. (Planned) Docker

A Docker test target is available for environments without local Python/Conda:

```powershell
make backend-test-docker
```

Under the hood it builds `apps/backend/Dockerfile.test` (dev + test deps) and runs `pytest -q`.
For iterative local development you can mount the source instead of rebuilding:

```powershell
docker run --rm -v ${PWD}/apps/backend:/app synthetic-data-platform/backend-test poetry run pytest -q
```

### Pytest Marks
- `e2e` (currently unregistered) — will be registered to remove PytestUnknownMarkWarning.

### End-to-End (E2E) Tests (Opt-In CI Job)

Full backend E2E tests are isolated under the `e2e` marker. They are skipped from normal CI via `-m "not e2e"`.

To run locally:
```powershell
cd apps/backend
pytest -m e2e -q
```

CI provides an opt-in job `backend-e2e` triggered by:
1. Manual dispatch of the workflow.
2. Nightly schedule (02:00 UTC).

The job spins up infra via `docker-compose up -d` under `./infra` and then executes `pytest -m e2e`.

### Common Warnings (Historical)
- FastAPI `on_event` deprecation — resolved via lifespan context.
- HTTP_422 constant deprecation — addressed (using `HTTP_422_UNPROCESSABLE_CONTENT`).

## Frontend Testing

Install dependencies and run tests:

```powershell
cd apps/frontend
pnpm install
pnpm test
```

The test environment uses MSW to intercept API calls. Handlers live in `src/tests/mocks/handlers.ts`. Add or override handlers inside individual tests when specific API shapes are needed.

### Adding a New Test
1. Create file under `apps/frontend/src/tests/` (or nested folder) with `.test.tsx` (React component) or `.test.ts` for logic.
2. Import utilities from `@testing-library/react`.
3. If network interaction is required, add a handler override:
```ts
import { server } from './mocks/server'
import { rest } from 'msw'

server.use(
  rest.get('/api/v1/example', (_req, res, ctx) => res(ctx.status(200), ctx.json({ value: 42 })))
)
```

## Combined Test Run

Run both suites via Make:
```powershell
make test
```

## Coverage

Coverage is enforced in CI with thresholds. Local runs can replicate these for visibility.

### Backend Coverage
CI command uses:
```powershell
pytest -m "not e2e" --cov=app --cov-report=xml --cov-fail-under=80
```
To run locally:
```powershell
cd apps/backend
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```
Adjust threshold with `--cov-fail-under=<percent>`.

### Frontend Coverage
Configured in `vitest.config.ts` with thresholds:
```
lines: 80, functions: 80, branches: 70, statements: 80
```
Local run:
```powershell
cd apps/frontend
pnpm vitest run --coverage
```
LCOV report at `apps/frontend/coverage/lcov.info` (uploaded in CI).

### Combined Make Targets (Planned)
You can extend the Makefile with targets like `backend-coverage`, `frontend-coverage`, and `coverage-all` (not yet added). For now invoke commands manually as above.

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| PytestUnknownMarkWarning (e2e) | Mark not registered | Add `markers = e2e: end-to-end tests` to pytest config or register in `conftest.py`. |
| FastAPI on_event deprecation | Using legacy startup/shutdown hooks | Refactor to lifespan context manager. |
| MSW unhandled request warning | Missing handler | Add explicit handler in `handlers.ts` or test override. |
| Slow backend test run | External services or large data | Use `-k` to narrow tests, add Docker target for consistency, or profile specific tests. |

## Roadmap
- Historical flakiness trend tracking (deferred)
- Makefile coverage targets (optional)

---
Last updated: 2025-11-08

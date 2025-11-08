# TODO

## Open
- [ ] P1: Enable PR coverage gates (branch protection)
	- Paths: Repository settings; `README.md` (docs)
	- Description: Configure branch protection to require Codecov project and patch checks with target thresholds; document the steps so maintainers can enable it.
	- Acceptance Criteria:
		- Branch protection requires Codecov project and patch checks (e.g., >= 80%)
		- README contains a short “Coverage gates” section with steps and thresholds
	- Notes: Requires repository admin permissions to enable.
- [ ] P2: Secret scan allowlist baseline
	- Paths: `.secrets.allowlist`, `.github/workflows/secret-scan.yml`
	- Description: Maintain a baseline of sanctioned secrets (e.g., non-sensitive test keys) to reduce false positives. Reference allowlist in secret scanning.
	- Acceptance Criteria:
		- Allowlist file exists and is used by workflow
		- Secret scan job excludes allowlisted fingerprints

- [ ] P2: SBOM attestation & image signing
	- Paths: `.github/workflows/ci.yml`
	- Description: Sign container images with cosign and attach SBOM attestations as part of the build.
	- Acceptance Criteria:
		- cosign step signs backend/frontend images
		- SBOM attestations uploaded as artifacts

- [ ] P2: SLO dashboard artifact
	- Paths: `scripts/`, `.github/workflows/*.yml`
	- Description: Aggregate performance placeholder metrics, coverage, flakiness, and test durations into a single JSON/Markdown snapshot for dashboards.
	- Acceptance Criteria:
		- Combined artifact produced per run
		- Markdown summary appended to the job

- [ ] P2: Test ordering drift detection
	- Paths: `scripts/`, `.github/workflows/ci.yml`
	- Description: Capture test execution order for Vitest and Pytest and compare with prior snapshot to detect ordering-dependent failures.
	- Acceptance Criteria:
		- Snapshot artifacts for order exist (current + previous)
		- Drift beyond threshold flags in summary

## Backlog (triaged)
- [ ] P2: Enable PR coverage gates (branch protection)
	- Paths: Repository settings
	- Description: Configure required status checks to enforce coverage gates (Codecov project/patch >= 80%).
	- Acceptance Criteria:
		- Branch protection enabled with Codecov checks required

## ✅ Done
- [x] 2025-11-09: SLO dashboard job stabilization — local; summary: Added `slo-dashboard` CI job to aggregate coverage, flakiness, durations, cache, deps, security, and image sizes into `slo-dashboard.{json,md}`.
- [x] 2025-11-09: Test ordering drift detection (self-contained) — local; summary: Implemented `scripts/test-ordering-drift.mjs` using regex-based XML parsing (no external deps), added CI job to snapshot and gate drift.
- [x] 2025-11-09: OpenAPI drift check (backend) — local; summary: Added `apps/backend/scripts/openapi_diff.py`, wired `openapi-drift` job in CI, and created unit test `apps/backend/tests/test_openapi_schema.py`; CI now fails on drift and uploads artifacts.
- [x] 2025-11-09: Secret scan allowlist baseline — local; summary: Introduced `.secrets.allowlist` and updated `.github/workflows/secret-scan.yml` to use `--baseline-path` to reduce false positives.
- [x] 2025-11-09: Cache efficiency report — local; summary: Aggregates pnpm/Poetry cache hits into `cache-efficiency.{json,md}` and appends a summary to the job.
- [x] 2025-11-09: Automated dependency update PRs (Renovate) — local; summary: `renovate.json` added with grouping and automerge, and README updated with enablement notes.
- [x] 2025-11-09: Coverage regression highlight — local; summary: CI PR comment now includes frontend coverage delta vs. base branch, with artifact uploaded.
- [x] 2025-11-09: Cache efficiency report — local; summary: CI collects pnpm/Poetry cache hit/miss and publishes a summary artifact/job summary.
- [x] 2025-11-09: Automated dependency update PRs (Renovate) — local; summary: Added renovate.json, documented enablement in README.
- [x] 2025-11-08: Canonicalize TODO to root using required template — local; summary: Root `TODO.md` now canonical, `README.md` updated to link it, and `docs/TODO.md` converted into a relocation pointer.
- [x] 2025-11-08: Resolve frontend ESLint warnings to satisfy max-warnings=0 — local; summary: Replaced `any` with safer types, added narrow helper for error extraction, tightened union types in tab selection, and added scoped `react-refresh/only-export-components` disables for hook/util exports.
- [x] 2025-11-08: Remove deprecated act warnings in frontend tests — local; summary: Upgraded @testing-library/react and migrated tests to user-event APIs, eliminating act warnings.
- [x] 2025-11-08: React Router v7 future flags — local; summary: Opted into v7_startTransition and v7_relativeSplatPath in `apps/frontend/src/main.tsx`.
- [x] 2025-11-08: Merge TESTING docs into docs/TESTING.md — local; summary: Consolidated testing guides and left root pointer.
- [x] 2025-11-08: Fix CI Vitest coverage provider — local; summary: Removed legacy c8 override; rely on `provider: 'v8'` in `vitest.config.ts`.
- [x] 2025-11-09: Dependency freshness job — CI collects outdated dependencies, merges JSON/Markdown, uploads artifacts.
- [x] 2025-11-09: Container image size capture — CI extracts image sizes, publishes JSON/Markdown + step summary.
- [x] 2025-11-09: Container image size trend — scheduled workflow publishes timestamped snapshots and latest aliases.
- [x] 2025-11-09: Flakiness threshold gate — added CI job to enforce flakiness rate <= 3% and max flaky count <= 10; fixed CI YAML structure.

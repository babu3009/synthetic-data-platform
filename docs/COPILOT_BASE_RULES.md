# Copilot Base Rules

This repository includes a PowerShell-based progress + logging pattern to standardize developer and CI task UX.

Key principles:

1. Always surface long-running work via `Write-Progress` with hierarchical (parent/child) bars.
2. Begin a transcript (`Start-Transcript`) for any task that mutates artifacts or performs multi-step logic; store logs in `artifacts/logs/` with timestamped filenames.
3. Provide deterministic exit codes: `0` success, `2` validation/usage error, `3` unexpected failure.
4. Avoid silent skips—emit warnings when an input file cannot be parsed or required properties are missing.
5. Keep modules self-contained: `ProgressTools.psm1` exports only logging and progress helpers and sets `Set-StrictMode` + `ErrorActionPreference = Stop` to fail fast.
6. Scripts must be side-effect free in dry-run mode (`-DryRun`), performing only parse/validation steps.
7. Prefer ordered JSON output for converter-style tasks to maximize diff readability in reviews.

Included Components:

- `scripts/ProgressTools/ProgressTools.psm1`: Module exporting `Start-TaskLogging`, `Stop-TaskLogging`, `New-ProgressContext`, `Set-Progress`, and `Complete-Progress`.
- `scripts/Invoke-TestAdapterConverter.ps1`: Example wrapper demonstrating transcript, progress bars, dry-run, and conversion with structured output.

Adoption Guidance:

When adding new automation scripts:
 - Place reusable helpers in a module under `scripts/<ModuleName>/<ModuleName>.psm1`.
 - Use the logging + progress primitives for any loop processing more than one item or any operation expected to exceed 1s.
 - Emit `[INFO]`, `[WARN]`, and `[ERROR]` prefixed lines for clarity in raw transcripts.
 - Return early with exit code `2` for precondition failures (missing directories, invalid arguments).

CI Integration:

Future GitHub Actions steps may invoke these scripts directly; transcripts give post-mortem visibility and progress output aids debugging on self-hosted runners or local replays.

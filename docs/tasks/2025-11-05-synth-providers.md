# Task Report — Synthetic Data Providers Framework

Date: 2025-11-05

## Summary
Implemented a deterministic, extensible provider framework for synthetic column data generation, plus tests. Providers share a consistent seeding scheme so results are reproducible per (global_seed, table, column).

- Base contract: `BaseProvider.sample(n, context) -> Iterable`
- Determinism: `seed = sha256(global_seed, table, column)`
- Uniqueness: `unique=True` enforces no duplicates when feasible
- ProviderRegistry: builds provider instances from JSON/dict configs or PII shorthand
- PII catalog: shortcuts for common PII (email, phone, name, dob, credit_card, etc.)

## Components
- `synth/providers/base.py`
  - `BaseProvider` Protocol
  - Deterministic RNG helper and `_hash_seed`
  - `UniqueMixin` for uniqueness enforcement
- `synth/providers/providers.py`
  - SequenceProvider, PatternProvider, CategoricalProvider, DateRangeProvider,
    ExpressionProvider (safe AST), GeoBoxProvider, ChecksumProvider (Luhn),
    ReferenceProvider, EmpiricalProvider (CSV), FakerProvider (optional)
- `synth/providers/registry.py`
  - `ProviderRegistry.from_config(...)`
  - `PII_CATALOG` with sensible defaults

## Files added/edited
- Added
  - `apps/backend/synth/__init__.py`
  - `apps/backend/synth/providers/base.py`
  - `apps/backend/synth/providers/providers.py`
  - `apps/backend/synth/providers/registry.py`
  - `apps/backend/tests/test_synth_providers.py`
- Updated
  - `apps/backend/requirements.txt` (added Faker; made backports.asyncio.runner conditional)
  - `apps/backend/environment.yml` (added faker)

## Tests
- File: `apps/backend/tests/test_synth_providers.py`
- Coverage:
  - Determinism for categorical/date_range/expression
  - Uniqueness for reference and empirical
  - Luhn checksum sanity
  - PII catalog shorthand works
- Result: All tests passed under the Miniforge `conda-synthetic-data` environment.

## How to run (PowerShell)
```powershell
cd apps/backend
$env:PYTHONPATH='.'
python -m pytest -q tests/test_synth_providers.py
```

## Notes
- `ExpressionProvider` uses a safe AST with whitelisted nodes and functions (subset of math, rng methods, and basic builtins).
- `FakerProvider` is optional; deterministic via `seed_instance` per context; `unique=True` uses Faker's uniqueness registry.

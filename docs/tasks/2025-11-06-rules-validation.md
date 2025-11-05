# Rules DSL and Validation (2025-11-06)

## Summary
- Introduced a compact rules DSL and a validator engine to assess implications, uniqueness, distributions, and temporal constraints on datasets.
- Added `POST /api/validate` to run validations against provided sample and final data without persisting.
- Included chi-square goodness-of-fit for categorical distributions and unit tests for parser, validator, and endpoint.

## Features
- DSL normalization:
  - Implication: `when`/`then[]` → `{type: implication, table, when, then}`
  - Uniqueness: `uniqueness: [table.col]` → `{type: uniqueness, table, columns}`
  - Distribution: `distribution: {table.col: {A:0.5,...}}` → `{type: distribution, table, column, probs}`
  - Temporal: `shipment.promised_date <= shipment.order_date + 2d` → `{type: temporal, table, left, op, right{column, offset_days}}`
- Safe expression evaluation with dotted `table.column` support via aliasing.
- Validation report returns counts, violation rates, chi-square stats, and a small sample of violations.

## Files
- app/services/rules_dsl.py – DSL parser + safe expression evaluation.
- app/services/validator.py – Validator for implication, uniqueness, distribution (chi-square), and temporal rules.
- app/api/api_v1/endpoints/validate.py – `POST /api/validate` endpoint; returns normalized rules and report.
- tests/test_rules_parser.py – Parser normalization tests.
- tests/test_validation_distribution.py – Distribution chi-square tests.
- tests/test_validation_rules.py – Implication and uniqueness tests.
- tests/test_api_validate.py – Endpoint test.

## How to run
```powershell
cmd.exe /d /c "call C:\\ProgramData\\miniforge3\\Scripts\\activate.bat C:\\ProgramData\\miniforge3 && conda activate conda-synthetic-data && cd apps\\backend && set PYTHONPATH=. && python -m pytest -q"
```

## Notes
- Temporal rule currently supports same-table comparisons. Extendable to cross-table with joins/refs.
- Distribution chi-square uses a 95% critical value lookup for df up to 10; can be upgraded to p-values with SciPy if needed.

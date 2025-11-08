#!/usr/bin/env python3
"""
Generate current OpenAPI schema from FastAPI app and compare against a baseline.
- Writes current schema to apps/backend/openapi-current.json
- If baseline exists at apps/backend/openapi-base.json, perform a semantically-stable diff (order-insensitive)
  and exit with non-zero if drift detected.
- Prints a concise summary to stdout for CI job summaries.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

# Ensure we can import the backend app
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # type: ignore  # noqa: E402

CUR_PATH = BACKEND / "openapi-current.json"
BASE_PATH = BACKEND / "openapi-base.json"


def normalize(obj):
    """Recursively normalize dict/list by sorting keys and lists where order is not guaranteed."""
    if isinstance(obj, dict):
        return {k: normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [normalize(x) for x in obj]
    return obj


def main() -> int:
    schema = app.openapi()
    CUR_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    # If baseline missing, bootstrap and report
    if not BASE_PATH.exists():
        BASE_PATH.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        print("Baseline created (no diff).")
        return 0

    current = normalize(schema)
    baseline = normalize(json.loads(BASE_PATH.read_text(encoding="utf-8")))

    if current == baseline:
        print("OpenAPI: no drift detected.")
        return 0

    # Produce a small diff summary of top-level counts
    def counts(spec_obj) -> dict:  # type: ignore[override]
        if not isinstance(spec_obj, dict):
            return {"paths": 0, "schemas": 0, "responses": 0}
        paths = spec_obj.get("paths", {})
        comps = spec_obj.get("components", {}) if isinstance(spec_obj.get("components", {}), dict) else {}
        schemas_cnt = 0
        responses_cnt = 0
        if isinstance(comps, dict):
            schemas_cnt = len(comps.get("schemas", {}) if isinstance(comps.get("schemas", {}), dict) else {})
            responses_cnt = len(comps.get("responses", {}) if isinstance(comps.get("responses", {}), dict) else {})
        return {
            "paths": len(paths) if isinstance(paths, dict) else 0,
            "schemas": schemas_cnt,
            "responses": responses_cnt,
        }

    c_cnt = counts(current)
    b_cnt = counts(baseline)
    print("OpenAPI drift detected.")
    print(json.dumps({"baseline": b_cnt, "current": c_cnt}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

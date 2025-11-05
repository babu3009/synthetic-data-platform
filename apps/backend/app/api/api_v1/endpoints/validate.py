from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app.services.rules_dsl import parse_rules
from app.services.validator import validate_rules


router = APIRouter()


@router.post("/validate")
async def validate(payload: Dict[str, Any]):
    """Validate a set of rules against provided sample and final datasets without persisting.

    Expected payload:
    {
      "rules": {...},  # DSL as specified
      "data_sample": {"table": [{...}, ...]},
      "data_final": {"table": [{...}, ...]},
      "max_violations": 10  # optional
    }
    """
    try:
        rules_norm = parse_rules(payload)
        data_sample = payload.get("data_sample", {})
        data_final = payload.get("data_final", {})
        max_violations = int(payload.get("max_violations", 10))
        report = validate_rules(rules_norm, data_sample, data_final, max_violations)
        return {"rules": rules_norm, "report": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

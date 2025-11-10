from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app.modules.synth.service import validate_payload as service_validate_payload


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
    return service_validate_payload(payload)

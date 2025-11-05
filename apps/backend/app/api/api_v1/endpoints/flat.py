from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app import crud, schemas
from app.db.models import ArtifactFormat, RequestStatus, RequestType
from app.services.flat import preview as preview_flat
from app.core.config import settings
from typing import Any, Dict, cast
from app.core.rq import get_queue
from app.jobs.flat_job import run_flat_job
from app.jobs.relational_job import run_relational_job
from rq import Retry  # type: ignore

router = APIRouter()
# Separate router for request-scoped actions under /requests
req_router = APIRouter()


@router.post("/preview")
async def flat_preview(payload: Dict[str, Any]):
    """Return first 100 rows for a flat schema preview."""
    try:
        rows = preview_flat(payload)
        return rows
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@req_router.post("/{request_id}:start", response_model=schemas.Request)
async def start_request(
    *, db: AsyncSession = Depends(get_db), request_id: UUID
) -> schemas.Request:
    req = await crud.request.get(db=db, id=request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Determine request type (Enum) directly from model
    rtype = getattr(req, "type", None)

    # Determine priority queue from request params (default -> "default")
    params = req.params_json or {}
    priority = "default"
    if isinstance(params, dict):
        priority = str(params.get("priority", "default")).lower()
        if priority not in {"low", "default", "high"}:
            priority = "default"

    # Enqueue background job with RQ and metadata
    q = cast(Any, get_queue(priority))
    if rtype == RequestType.FLAT:
        job = q.enqueue(
            run_flat_job,
            str(request_id),
            meta={"request_id": str(request_id)},
            retry=Retry(max=3),
        )
    elif rtype == RequestType.RELATIONAL:
        job = q.enqueue(
            run_relational_job,
            str(request_id),
            meta={"request_id": str(request_id)},
            retry=Retry(max=3),
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported request type for start")

    # Stash job id in params and keep status as PENDING (worker will set RUNNING)
    updated_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        updated_params = {**params}
    updated_params["job_id"] = job.get_id()
    updated_params["queue"] = priority
    await crud.request.update(db=db, db_obj=req, obj_in={"params_json": updated_params})

    # Return refreshed request
    req = await crud.request.get(db=db, id=request_id)
    return req

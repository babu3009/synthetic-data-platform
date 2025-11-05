from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app import crud, schemas
from app.db.models import ArtifactFormat, RequestStatus, RequestType
from app.services.flat import preview as preview_flat, generate_to_artifacts
from app.services.storage import get_storage
from app.core.config import settings
from typing import Any, Dict, cast
from app.core.rq import get_queue
from app.jobs.flat_job import run_flat_job

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
    # Pylance may see SQLAlchemy InstrumentedAttribute here; compare via string to avoid typing issues
    if str(getattr(req, "type", "")) != RequestType.FLAT:
        raise HTTPException(status_code=400, detail="Only flat requests are supported here")

    # Enqueue background job with RQ
    q = cast(Any, get_queue())
    job = q.enqueue(run_flat_job, str(request_id))

    # Stash job id in params and keep status as PENDING (worker will set RUNNING)
    params = req.params_json or {}
    updated_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        updated_params = {**params}
    updated_params["job_id"] = job.get_id()
    await crud.request.update(db=db, db_obj=req, obj_in={"params_json": updated_params})

    # Return refreshed request
    req = await crud.request.get(db=db, id=request_id)
    return req

from __future__ import annotations

from pathlib import Path
import os
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app import crud, schemas
from app.db.models import ArtifactFormat, RequestStatus, RequestType, ProjectRole
from app.security.auth import require_project_scope, get_current_principal
from app.modules.synth.service import flat_preview as service_flat_preview, start_request_job as service_start_request_job
from app.core.config import settings
from typing import Any, Dict, cast
from app.core.rq import get_queue
from app.jobs.flat_job import run_flat_job
from app.jobs.relational_job import run_relational_job
from rq import Retry  # type: ignore
from app.observability import REQUESTS_STARTED

router = APIRouter()
# Separate router for request-scoped actions under /requests
req_router = APIRouter()


@router.post("/preview")
async def flat_preview(payload: Dict[str, Any]):
    """Return first 100 rows for a flat schema preview."""
    return service_flat_preview(payload)


@req_router.post("/{request_id}:start", response_model=schemas.Request)
async def start_request(
    *, db: AsyncSession = Depends(get_db), request_id: UUID, principal = Depends(get_current_principal)
) -> schemas.Request:
    req = await crud.request.get(db=db, id=request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Authorization: require run:request or EDITOR/OWNER on the project
    await require_project_scope(str(req.project_id), required_scopes=["run:request"], required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    # Return refreshed request
    # Pass module-level get_queue so tests can monkeypatch flat_endpoint.get_queue
    return await service_start_request_job(db, request_id=request_id, get_queue_fn=get_queue)

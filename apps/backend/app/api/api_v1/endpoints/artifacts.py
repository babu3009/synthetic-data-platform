"""
Artifacts API endpoints.
"""
from typing import List
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db
from app.modules.storage.service import (
    list_artifacts as service_list_artifacts,
    get_artifact as service_get_artifact,
    sign_artifact as service_sign_artifact,
)
from app.security.auth import require_project_scope, get_current_principal
from app.db.models import ProjectRole

router = APIRouter()


# Compatibility route that handles paths like /artifacts/{uuid}:sign
@router.get("/{request_id}/artifacts/{artifact_and_action}")
async def sign_artifact_url(
    *,
    db: AsyncSession = Depends(get_db),
    request_id: UUID,
    artifact_and_action: str,
    expires: int = 3600,
    principal = Depends(get_current_principal),
) -> dict:
    """Return a signed URL for an artifact when called as /{artifact_id}:sign.

    Extracts the UUID part before the colon and generates a signed URL.
    """
    if not artifact_and_action.endswith(":sign"):
        raise HTTPException(status_code=404, detail="Not found")
    artifact_id_str = artifact_and_action.split(":", 1)[0]
    try:
        artifact_id = uuid.UUID(artifact_id_str)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid artifact id")

    # Reuse the same logic as the primary endpoint
    request_obj = await crud.request.get(db=db, id=request_id)
    if not request_obj:
        raise HTTPException(status_code=404, detail="Request not found")
    await require_project_scope(str(request_obj.project_id), required_scopes=["read:artifacts"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_sign_artifact(db, request_id=request_id, artifact_id=artifact_id, expires=int(expires))


@router.get("/{request_id}/artifacts", response_model=List[schemas.Artifact])
async def read_artifacts(
    *,
    db: AsyncSession = Depends(get_db),
    request_id: UUID,
    principal = Depends(get_current_principal),
) -> List[schemas.Artifact]:
    """
    Get artifacts for a request.
    """
    request = await crud.request.get(db=db, id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    await require_project_scope(str(request.project_id), required_scopes=["read:artifacts"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_list_artifacts(db, request_id=request_id)


@router.get("/{request_id}/artifacts/{artifact_id}", response_model=schemas.Artifact)
async def read_artifact(
    *,
    db: AsyncSession = Depends(get_db),
    request_id: UUID,
    artifact_id: UUID,
    principal = Depends(get_current_principal),
) -> schemas.Artifact:
    """
    Get specific artifact by ID.
    """
    request = await crud.request.get(db=db, id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    await require_project_scope(str(request.project_id), required_scopes=["read:artifacts"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_get_artifact(db, request_id=request_id, artifact_id=artifact_id)
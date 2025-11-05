"""
Artifacts API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db

router = APIRouter()


@router.get("/{request_id}/artifacts", response_model=List[schemas.Artifact])
async def read_artifacts(
    *,
    db: AsyncSession = Depends(get_db),
    request_id: UUID,
) -> List[schemas.Artifact]:
    """
    Get artifacts for a request.
    """
    # Verify request exists
    request = await crud.request.get(db=db, id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    artifacts = await crud.artifact.get_by_request(db, request_id=request_id)
    return artifacts


@router.get("/{request_id}/artifacts/{artifact_id}", response_model=schemas.Artifact)
async def read_artifact(
    *,
    db: AsyncSession = Depends(get_db),
    request_id: UUID,
    artifact_id: UUID,
) -> schemas.Artifact:
    """
    Get specific artifact by ID.
    """
    # Verify request exists
    request = await crud.request.get(db=db, id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    artifact = await crud.artifact.get(db=db, id=artifact_id)
    if not artifact or artifact.request_id != request_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact
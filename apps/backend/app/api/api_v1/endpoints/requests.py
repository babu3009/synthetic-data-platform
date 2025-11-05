"""
Requests API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db

router = APIRouter()


@router.post("/", response_model=schemas.Request)
async def create_request(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request_in: schemas.RequestCreate,
) -> schemas.Request:
    """
    Create new synthetic data request for a project.
    """
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    request = await crud.request.create_with_project(
        db=db, obj_in=request_in, project_id=project_id
    )
    return request


@router.get("/", response_model=List[schemas.Request])
async def read_requests(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.Request]:
    """
    Retrieve requests for a project.
    """
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    requests = await crud.request.get_by_project(
        db, project_id=project_id, skip=skip, limit=limit
    )
    return requests


@router.get("/{request_id}", response_model=schemas.Request)
async def read_request(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request_id: UUID,
) -> schemas.Request:
    """
    Get request by ID.
    """
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    request = await crud.request.get(db=db, id=request_id)
    if not request or request.project_id != project_id:
        raise HTTPException(status_code=404, detail="Request not found")
    return request
"""
Requests API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db
from app.security.auth import require_project_scope, get_current_principal
from app.db.models import ProjectRole

router = APIRouter()


@router.post("/", response_model=schemas.Request)
async def create_request(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request_in: schemas.RequestCreate,
    principal = Depends(get_current_principal),
) -> schemas.Request:
    """
    Create new synthetic data request for a project.
    """
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization: require write scope or EDITOR/OWNER
    await require_project_scope(str(project_id), required_scopes=["write:project"], required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)

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
    principal = Depends(get_current_principal),
) -> List[schemas.Request]:
    """
    Retrieve requests for a project.
    """
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization: require read scope or VIEWER+
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)

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
    principal = Depends(get_current_principal),
) -> schemas.Request:
    """
    Get request by ID.
    """
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization: require read scope or VIEWER+
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)

    request = await crud.request.get(db=db, id=request_id)
    if not request or request.project_id != project_id:
        raise HTTPException(status_code=404, detail="Request not found")
    return request
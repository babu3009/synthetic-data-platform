"""
Requests API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.modules.synth.service import create_request as service_create_request, list_requests as service_list_requests, get_request as service_get_request, estimate_request as service_estimate_request
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
    # Authorization: require write scope or EDITOR/OWNER
    await require_project_scope(str(project_id), required_scopes=["write:project"], required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_create_request(db, project_id=project_id, request_in=request_in)


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
    # Authorization: require read scope or VIEWER+
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_list_requests(db, project_id=project_id, skip=skip, limit=limit)


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
    # Authorization: require read scope or VIEWER+
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_get_request(db, project_id=project_id, request_id=request_id)


@router.post("/{request_id}:estimate", response_model=dict)
async def estimate_request(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request_id: UUID,
    principal = Depends(get_current_principal),
) -> dict:
    """
    Estimate size and time for a request based on its current params.

    Returns a JSON with estimated total_rows, bytes (csv/parquet), and time.
    """
    # Authorization: read scope or VIEWER+
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    return await service_estimate_request(db, project_id=project_id, request_id=request_id)


@router.delete("/{request_id}", status_code=204)
async def delete_request(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request_id: UUID,
    principal = Depends(get_current_principal),
) -> None:
    """
    Delete a request by ID.
    """
    # Authorization: require write scope or EDITOR/OWNER
    await require_project_scope(str(project_id), required_scopes=["write:project"], required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    
    # Get the request to ensure it exists and belongs to the project
    req = await service_get_request(db, project_id=project_id, request_id=request_id)
    
    # Delete the request
    await crud.request.remove(db=db, id=request_id)
    await db.commit()


@router.post("/{request_id}:restart", response_model=schemas.Request, status_code=201)
async def restart_request(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    request_id: UUID,
    principal = Depends(get_current_principal),
) -> schemas.Request:
    """
    Restart a completed/failed request by creating a new request with the same configuration.
    Generates new synthetic data with a different seed.
    """
    # Authorization: require write scope or EDITOR/OWNER
    await require_project_scope(str(project_id), required_scopes=["write:project"], required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    
    # Get the original request
    original = await service_get_request(db, project_id=project_id, request_id=request_id)
    
    # Create a new request with the same configuration but a new seed
    import random
    new_seed = random.randint(1, 2**31 - 1)
    
    request_in = schemas.RequestCreate(
        type=original.type,
        params_json=original.params_json,
        seed=new_seed,
        alias=f"{original.alias or 'request'}-restart" if original.alias else None
    )
    
    return await service_create_request(db, project_id=project_id, request_in=request_in)
"""
Requests API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.services.estimator import estimate_relational
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
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization: read scope or VIEWER+
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)

    req = await crud.request.get(db=db, id=request_id)
    if not req or req.project_id != project_id:
        raise HTTPException(status_code=404, detail="Request not found")

    params = req.params_json or {}
    schema = params.get("schema") or params.get("config")
    if not schema:
        raise HTTPException(status_code=400, detail="Missing schema in request params_json")
    rows_per_table = params.get("rows_per_table", {})
    # route by request type
    if str(req.type) == "relational":
        return estimate_relational(schema, rows_per_table)
    elif str(req.type) == "flat":
        total_rows = int(params.get("rows", 0) or 0)
        temp_schema = {"tables": [{"name": "data", "columns": schema.get("fields", [])}]}
        rp = {"data": total_rows}
        return estimate_relational(temp_schema, rp)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported request type for estimate: {req.type}")
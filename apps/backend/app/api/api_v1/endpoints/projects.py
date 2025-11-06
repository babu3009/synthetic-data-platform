"""
Projects API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db
from app.security.auth import get_current_principal, require_project_scope
from app.db.models import ProjectRole

router = APIRouter()


@router.post("/", response_model=schemas.Project)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: schemas.ProjectCreate,
) -> schemas.Project:
    """
    Create new project.
    """
    # Check if project name already exists for this owner
    existing = await crud.project.get_by_name_and_owner(
        db, name=project_in.name, owner=project_in.owner
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Project with this name already exists for this owner",
        )
    
    project = await crud.project.create(db=db, obj_in=project_in)
    return project


@router.get("/", response_model=List[schemas.Project])
async def read_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    principal = Depends(get_current_principal),
) -> List[schemas.Project]:
    """
    Retrieve projects.
    """
    # If authenticated via API key, only return the owning project if scope allows
    if principal and getattr(principal, "kind", None) == "api_key":
        # require read:project scope
        await require_project_scope(principal.project_id, required_scopes=["read:project"], principal=principal, db=db)
        proj = await crud.project.get(db, id=principal.project_id)
        return [proj] if proj else []

    # Otherwise, return all (or later: filter by membership)
    projects = await crud.project.get_multi(db, skip=skip, limit=limit)
    return projects


@router.get("/{project_id}", response_model=schemas.Project)
async def read_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    principal = Depends(get_current_principal),
) -> schemas.Project:
    """
    Get project by ID.
    """
    # Authorization: require read scope or viewer role
    await require_project_scope(str(project_id), required_scopes=["read:project"], required_roles=[ProjectRole.VIEWER, ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=schemas.Project)
async def update_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    project_in: schemas.ProjectUpdate,
    principal = Depends(get_current_principal),
) -> schemas.Project:
    """
    Update a project.
    """
    # Authorization: require write scope or EDITOR/OWNER
    await require_project_scope(str(project_id), required_scopes=["write:project"], required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER], principal=principal, db=db)
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await crud.project.update(db=db, db_obj=project, obj_in=project_in)
    return project


@router.delete("/{project_id}", response_model=schemas.Project)
async def delete_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    principal = Depends(get_current_principal),
) -> schemas.Project:
    """
    Delete a project.
    """
    # Authorization: require OWNER role
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await crud.project.remove(db=db, id=project_id)
    return project
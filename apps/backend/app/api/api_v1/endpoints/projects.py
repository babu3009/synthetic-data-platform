"""
Projects API endpoints.
"""
from typing import List
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db
from app.security.auth import get_current_principal, require_project_scope
from app.db.models import ProjectRole, Project, ProjectMember
from sqlalchemy import select, func

router = APIRouter()


@router.post("/", response_model=schemas.Project)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: schemas.ProjectCreate,
    principal = Depends(get_current_principal),
) -> schemas.Project:
    """
    Create new project.
    """
    # Prefer user-id ownership when authenticated
    owner_user_id = None
    if principal and getattr(principal, "kind", None) == "user" and getattr(principal, "user_id", None):
        try:
            owner_user_id = UUID(str(principal.user_id))
        except Exception:
            owner_user_id = None

    if owner_user_id is not None:
        # Enforce uniqueness by (owner_user_id, name)
        existing = await crud.project.get_by_name_and_owner_user_id(
            db, name=project_in.name, owner_user_id=owner_user_id
        )
        if existing:
            raise HTTPException(status_code=400, detail="Project with this name already exists for this owner")

        # Create ORM directly to set owner_user_id
        db_obj = Project(
            name=project_in.name,
            tags=project_in.tags or [],
            webhook_run_status_url=project_in.webhook_run_status_url,
            artifact_ttl_days=project_in.artifact_ttl_days,
            owner_user_id=owner_user_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # Create owner membership record so user can access the project
        owner_member = ProjectMember(
            project_id=db_obj.id,
            user_id=owner_user_id,
            role=ProjectRole.OWNER,
        )
        db.add(owner_member)
        await db.commit()
        
        return db_obj

    # Fallback: legacy email-based ownership (no uniqueness pre-check in SQLite tests)
    project = await crud.project.create(db=db, obj_in=project_in)
    return project


@router.get("/search", response_model=List[str])
async def search_project_names(
    *,
    db: AsyncSession = Depends(get_db),
    q: str = "",
    principal = Depends(get_current_principal),
) -> List[str]:
    """Search project names for the current user (for validation/autocomplete)."""
    if not principal or getattr(principal, "kind", None) != "user" or not principal.user_id:
        return []
    
    try:
        typed_user_id = UUID(str(principal.user_id))
    except Exception:
        return []
    
    # Get all project names for this user
    query = (
        select(Project.name)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == typed_user_id)
    )
    
    if q:
        query = query.where(func.lower(Project.name).contains(func.lower(q)))
    
    res = await db.execute(query)
    return res.scalars().all()


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

    # If authenticated user principal, filter by membership (VIEWER/EDITOR/OWNER)
    if principal and getattr(principal, "kind", None) == "user":
        # If user_id is not set, return empty list (user not in system yet)
        if not principal.user_id:
            return []
        # Join by user_id only (legacy user_sub removed)
        try:
            typed_user_id = UUID(str(principal.user_id))
        except Exception:
            return []
        q = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == typed_user_id)
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(q)
        return res.scalars().all()

    # If no principal: honor AUTH_DISABLED for dev, otherwise require auth
    if os.getenv("AUTH_DISABLED", "").lower() in {"1", "true", "yes"}:
        return await crud.project.get_multi(db, skip=skip, limit=limit)
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Not authenticated")


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
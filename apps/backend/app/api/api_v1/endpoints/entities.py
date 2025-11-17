"""
API endpoints for wizard entity management.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.db.models import WizardEntity, Project

router = APIRouter()


class EntitySchema(BaseModel):
    """Entity schema for wizard configuration."""
    tables: List[dict] = Field(default_factory=list)
    relationships: List[dict] | None = Field(default=None)
    layout: dict | None = Field(default=None)


class EntityCreate(BaseModel):
    """Create entity request."""
    id: str | None = Field(None, description="Optional UUID for entity. If not provided, one will be generated.")
    name: str = Field(..., min_length=1, max_length=255)
    schema: EntitySchema


class EntityUpdate(BaseModel):
    """Update entity request."""
    name: str | None = Field(None, min_length=1, max_length=255)
    schema: EntitySchema | None = None


class EntityResponse(BaseModel):
    """Entity response."""
    id: str
    project_id: str
    name: str
    schema: dict
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=EntityResponse, status_code=201)
async def create_entity(
    project_id: UUID,
    entity: EntityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new wizard entity configuration."""
    # Verify project exists
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create entity
    entity_kwargs = {
        "project_id": project_id,
        "name": entity.name,
        "schema_json": entity.schema.model_dump(),
    }
    # Use provided ID if valid UUID string, otherwise let DB generate
    if entity.id:
        try:
            entity_kwargs["id"] = UUID(entity.id)
        except (ValueError, AttributeError):
            pass  # Let DB generate UUID
    
    db_entity = WizardEntity(**entity_kwargs)
    db.add(db_entity)
    await db.commit()
    await db.refresh(db_entity)
    
    return EntityResponse(
        id=str(db_entity.id),
        project_id=str(db_entity.project_id),
        name=db_entity.name,
        schema=db_entity.schema_json,
        created_at=db_entity.created_at.isoformat(),
        updated_at=db_entity.updated_at.isoformat(),
    )


@router.get("", response_model=List[EntityResponse])
async def list_entities(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all wizard entities for a project."""
    stmt = (
        select(WizardEntity)
        .where(WizardEntity.project_id == project_id)
        .order_by(WizardEntity.updated_at.desc())
    )
    result = await db.execute(stmt)
    entities = result.scalars().all()
    
    return [
        EntityResponse(
            id=str(e.id),
            project_id=str(e.project_id),
            name=e.name,
            schema=e.schema_json,
            created_at=e.created_at.isoformat(),
            updated_at=e.updated_at.isoformat(),
        )
        for e in entities
    ]


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    project_id: UUID,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific wizard entity."""
    stmt = select(WizardEntity).where(
        WizardEntity.id == entity_id,
        WizardEntity.project_id == project_id,
    )
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return EntityResponse(
        id=str(entity.id),
        project_id=str(entity.project_id),
        name=entity.name,
        schema=entity.schema_json,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    project_id: UUID,
    entity_id: UUID,
    update: EntityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a wizard entity."""
    stmt = select(WizardEntity).where(
        WizardEntity.id == entity_id,
        WizardEntity.project_id == project_id,
    )
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if update.name is not None:
        entity.name = update.name
    if update.schema is not None:
        entity.schema_json = update.schema.model_dump()
    
    await db.commit()
    await db.refresh(entity)
    
    return EntityResponse(
        id=str(entity.id),
        project_id=str(entity.project_id),
        name=entity.name,
        schema=entity.schema_json,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    project_id: UUID,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a wizard entity."""
    stmt = select(WizardEntity).where(
        WizardEntity.id == entity_id,
        WizardEntity.project_id == project_id,
    )
    result = await db.execute(stmt)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    await db.delete(entity)
    await db.commit()

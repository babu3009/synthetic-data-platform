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
    description: str | None = Field(None, description="Optional description of the entity")
    schema: EntitySchema
    rules_config: str | None = Field(None, description="YAML or JSON rules configuration")
    rules_format: str | None = Field(None, description="Format of rules_config: 'yaml' or 'json'")


class EntityUpdate(BaseModel):
    """Update entity request."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, description="Optional description of the entity")
    schema: EntitySchema | None = None
    rules_config: str | None = Field(None, description="YAML or JSON rules configuration")
    rules_format: str | None = Field(None, description="Format of rules_config: 'yaml' or 'json'")


class EntityResponse(BaseModel):
    """Entity response."""
    id: str
    project_id: str
    name: str
    description: str | None = None
    version: int
    schema: dict
    rules_config: str | None = None
    rules_format: str | None = None
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
        "description": entity.description,
        "schema_json": entity.schema.model_dump(),
        "rules_config": entity.rules_config,
        "rules_format": entity.rules_format,
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
        description=db_entity.description,
        version=db_entity.version,
        schema=db_entity.schema_json,
        rules_config=db_entity.rules_config,
        rules_format=db_entity.rules_format,
        created_at=db_entity.created_at.isoformat(),
        updated_at=db_entity.updated_at.isoformat(),
    )


@router.get("", response_model=list[EntityResponse])
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
            description=e.description,
            version=e.version,
            schema=e.schema_json,
            rules_config=e.rules_config,
            rules_format=e.rules_format,
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
    if update.description is not None:
        entity.description = update.description
    if update.schema is not None:
        entity.schema_json = update.schema.model_dump()
    if update.rules_config is not None:
        entity.rules_config = update.rules_config
    if update.rules_format is not None:
        entity.rules_format = update.rules_format
    
    # Increment version on any update
    entity.version += 1
    
    await db.commit()
    await db.refresh(entity)
    
    return EntityResponse(
        id=str(entity.id),
        project_id=str(entity.project_id),
        name=entity.name,
        description=entity.description,
        version=entity.version,
        schema=entity.schema_json,
        rules_config=entity.rules_config,
        rules_format=entity.rules_format,
        created_at=entity.created_at.isoformat(),
        updated_at=entity.updated_at.isoformat(),
    )


@router.delete("/{entity_id}")
@router.put("/{entity_id}", response_model=EntityResponse)
@router.put("/{entity_id}", response_model=EntityResponse)
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

"""
Sources API endpoints for DDL ingestion and schema management.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.db import models
from app.db.session import get_db
from app.modules.synth.service import (
    upload_source as service_upload_source,
    get_source_schema as service_get_source_schema,
    get_source_dag as service_get_source_dag,
    get_source_tables as service_get_source_tables,
    list_sources as service_list_sources,
)

router = APIRouter()


def compute_checksum(content: bytes) -> str:
    """Compute SHA-256 checksum of file content."""
    return hashlib.sha256(content).hexdigest()


async def save_upload(content: bytes, filename: str, project_id: UUID) -> str:
    """
    Save uploaded file to storage.
    
    In production, this would save to S3/Azure Blob/etc.
    For now, saves to local filesystem.
    
    Returns:
        Storage URI
    """
    storage_dir = Path("storage") / "sources" / str(project_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = uuid4()
    file_path = storage_dir / f"{file_id}_{filename}"
    
    file_path.write_bytes(content)
    
    return f"file://{file_path.absolute()}"


@router.post("/", response_model=schemas.SourceUploadResponse)
async def upload_source(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    file: UploadFile = File(...),
    dialect: Optional[str] = Form("postgres"),
) -> schemas.SourceUploadResponse:
    return await service_upload_source(db, project_id=project_id, file=file, dialect=dialect)


@router.get("/", response_model=list[schemas.Source])
async def list_project_sources(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
):
    return await service_list_sources(db, project_id=project_id, skip=skip, limit=limit)


@router.get("/{source_id}", response_model=schemas.SchemaResponse)
async def get_source_schema(
    *,
    db: AsyncSession = Depends(get_db),
    source_id: UUID,
) -> schemas.SchemaResponse:
    return await service_get_source_schema(db, source_id=source_id)


@router.get("/{source_id}/dag", response_model=schemas.DAGSchema)
async def get_source_dag(
    *,
    db: AsyncSession = Depends(get_db),
    source_id: UUID,
) -> schemas.DAGSchema:
    return await service_get_source_dag(db, source_id=source_id)


@router.get("/{source_id}/tables", response_model=list[schemas.TableSchema])
async def get_source_tables(
    *,
    db: AsyncSession = Depends(get_db),
    source_id: UUID,
) -> list[schemas.TableSchema]:
    result = await service_get_source_tables(db, source_id=source_id)
    return list(result)

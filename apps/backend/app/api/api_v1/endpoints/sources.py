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
from app.utils.ddl_parser import parse_ddl, validate_schema

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
    """
    Upload and parse a DDL or schema JSON file.
    
    - **project_id**: UUID of the project (from path)
    - **file**: DDL SQL file (.sql) or schema JSON file (.json)
    - **dialect**: SQL dialect (postgres/mysql/mssql/hana) - only used for DDL files
    
    Returns parsed schema with warnings.
    """
    # Check if project exists
    result = await db.execute(
        select(models.Project).where(models.Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Read file content
    content = await file.read()
    checksum = compute_checksum(content)
    
    # Determine source kind and parse
    filename = file.filename or "unknown"
    if filename.endswith(".json"):
        kind = models.SourceKind.JSON
        try:
            schema_dict = json.loads(content.decode("utf-8"))
            canonical_schema = schemas.CanonicalSchema(**schema_dict)
            # Validate the schema
            additional_warnings = validate_schema(canonical_schema)
            canonical_schema.warnings.extend(additional_warnings)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid schema format: {str(e)}")
    
    elif filename.endswith(".sql") or filename.endswith(".ddl"):
        kind = models.SourceKind.DDL
        try:
            ddl_content = content.decode("utf-8")
            canonical_schema = parse_ddl(ddl_content, dialect=dialect or "postgres")
            # Validate the parsed schema
            additional_warnings = validate_schema(canonical_schema)
            canonical_schema.warnings.extend(additional_warnings)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"DDL parsing error: {str(e)}")
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload .sql, .ddl, or .json file"
        )
    
    # Save file to storage
    storage_uri = await save_upload(content, filename, project_id)
    
    # Create source record
    source = models.Source(
        project_id=project_id,
        kind=kind,
        storage_uri=storage_uri,
        checksum=checksum
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)
    
    # Store IDs before they expire
    source_id = source.id
    
    # Create schema record
    schema_record = models.Schema(
        source_id=source_id,
        schema_json=canonical_schema.model_dump(),
        dag_json=canonical_schema.dag.model_dump(),
        warnings=canonical_schema.warnings
    )
    db.add(schema_record)
    await db.commit()
    await db.refresh(schema_record)
    schema_id = schema_record.id
    
    return schemas.SourceUploadResponse(
        source_id=source_id,
        schema_id=schema_id,
        kind=kind.value,
        tables_count=len(canonical_schema.tables),
        warnings=canonical_schema.warnings
    )


@router.get("/{source_id}", response_model=schemas.SchemaResponse)
async def get_source_schema(
    *,
    db: AsyncSession = Depends(get_db),
    source_id: UUID,
) -> schemas.SchemaResponse:
    """
    Get parsed schema for a source.
    
    Returns normalized schema JSON and DAG.
    """
    # Find schema by source_id
    result = await db.execute(
        select(models.Schema).where(models.Schema.source_id == source_id)
    )
    schema_record = result.scalar_one_or_none()
    
    if not schema_record:
        raise HTTPException(status_code=404, detail="Schema not found for this source")
    
    # Parse schema JSON
    canonical_schema = schemas.CanonicalSchema(**schema_record.schema_json)
    dag = schemas.DAGSchema(**schema_record.dag_json)
    
    return schemas.SchemaResponse(
        id=schema_record.id,
        source_id=schema_record.source_id,
        schema=canonical_schema,
        dag=dag,
        warnings=schema_record.warnings,
        created_at=schema_record.created_at
    )


@router.get("/{source_id}/dag", response_model=schemas.DAGSchema)
async def get_source_dag(
    *,
    db: AsyncSession = Depends(get_db),
    source_id: UUID,
) -> schemas.DAGSchema:
    """
    Get dependency DAG for a source schema.
    
    Returns the table dependency graph.
    """
    result = await db.execute(
        select(models.Schema).where(models.Schema.source_id == source_id)
    )
    schema_record = result.scalar_one_or_none()
    
    if not schema_record:
        raise HTTPException(status_code=404, detail="Schema not found for this source")
    
    return schemas.DAGSchema(**schema_record.dag_json)


@router.get("/{source_id}/tables", response_model=list[schemas.TableSchema])
async def get_source_tables(
    *,
    db: AsyncSession = Depends(get_db),
    source_id: UUID,
) -> list[schemas.TableSchema]:
    """
    Get list of tables in a source schema.
    """
    result = await db.execute(
        select(models.Schema).where(models.Schema.source_id == source_id)
    )
    schema_record = result.scalar_one_or_none()
    
    if not schema_record:
        raise HTTPException(status_code=404, detail="Schema not found for this source")
    
    canonical_schema = schemas.CanonicalSchema(**schema_record.schema_json)
    return canonical_schema.tables

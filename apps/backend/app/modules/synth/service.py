"""Synth module service layer (Phase 2).

Centralizes core logic for sources, requests, artifacts, validation, and
flat preview / job start while preserving existing behavior.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Callable, Optional, Sequence, Mapping, cast
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db import models
from app.modules.synth.generators.flat_generator import preview as preview_flat
from app.services.estimator import estimate_relational
from app.utils.ddl_parser import parse_ddl, validate_schema
from app.services.rules_dsl import parse_rules
from app.services.validator import validate_rules
from app.services.storage import get_storage
from app.modules.storage.service import sign_artifact as storage_sign_artifact
from app.db.models import RequestType
from app.core.rq import get_queue
from app.jobs.flat_job import run_flat_job
from app.jobs.relational_job import run_relational_job
from rq import Retry  # type: ignore
from typing import cast
from app.observability import REQUESTS_STARTED


# ---------- Sources ----------

def _compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def _save_upload(content: bytes, filename: str, project_id: UUID) -> str:
    storage_dir = Path("storage") / "sources" / str(project_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid4()
    file_path = storage_dir / f"{file_id}_{filename}"
    file_path.write_bytes(content)
    return f"file://{file_path.absolute()}"


async def upload_source(
    db: AsyncSession,
    *,
    project_id: UUID,
    file: UploadFile,
    dialect: str | None = "postgres",
) -> schemas.SourceUploadResponse:
    # Verify project exists
    project = await crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    checksum = _compute_checksum(content)
    filename = file.filename or "unknown"

    # Parse schema
    if filename.endswith(".json"):
        try:
            schema_dict = json.loads(content.decode("utf-8"))
            canonical_schema = schemas.CanonicalSchema(**schema_dict)
            additional_warnings = validate_schema(canonical_schema)
            canonical_schema.warnings.extend(additional_warnings)
            kind = models.SourceKind.JSON
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid schema format: {str(e)}")
    elif filename.endswith(".sql") or filename.endswith(".ddl"):
        try:
            ddl_content = content.decode("utf-8")
            canonical_schema = parse_ddl(ddl_content, dialect=dialect or "postgres")
            additional_warnings = validate_schema(canonical_schema)
            canonical_schema.warnings.extend(additional_warnings)
            kind = models.SourceKind.DDL
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"DDL parsing error: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload .sql, .ddl, or .json file")

    storage_uri = await _save_upload(content, filename, project_id)

    # Create source record
    source = models.Source(
        project_id=project_id,
        kind=kind,
        storage_uri=storage_uri,
        checksum=checksum,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)
    source_id = source.id

    schema_record = models.Schema(
        source_id=source_id,
        schema_json=canonical_schema.model_dump(),
        dag_json=canonical_schema.dag.model_dump(),
        warnings=canonical_schema.warnings,
    )
    db.add(schema_record)
    await db.commit()
    await db.refresh(schema_record)

    return schemas.SourceUploadResponse(
        source_id=source_id,
        schema_id=schema_record.id,
        kind=kind.value,
        tables_count=len(canonical_schema.tables),
        warnings=canonical_schema.warnings,
    )


async def list_sources(db: AsyncSession, *, project_id: UUID, skip: int = 0, limit: int = 100):
    """List sources for a project.

    Returns lightweight Source schemas suitable for list views.
    """
    project = await crud.project.get(db=db, id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    res = await db.execute(
        select(models.Source)
        .where(models.Source.project_id == project_id)
        .order_by(models.Source.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sources = list(res.scalars().all())
    # Pydantic model configured with from_attributes, FastAPI can serialize ORM models directly
    return sources


async def get_source_schema(db: AsyncSession, *, source_id: UUID) -> schemas.SchemaResponse:
    res = await db.execute(select(models.Schema).where(models.Schema.source_id == source_id))
    schema_record = res.scalar_one_or_none()
    if schema_record is None:
        raise HTTPException(status_code=404, detail="Schema not found for this source")
    # Cast to Mapping[str, Any] for static type checkers
    canonical_schema = schemas.CanonicalSchema(**cast(Mapping[str, Any], schema_record.schema_json))
    dag = schemas.DAGSchema(**cast(Mapping[str, Any], schema_record.dag_json))
    return schemas.SchemaResponse(
        id=cast(UUID, schema_record.id),
        source_id=cast(UUID, schema_record.source_id),
        canonical_schema=canonical_schema,
        dag=dag,
        warnings=list(schema_record.warnings or []),
        created_at=cast(Any, schema_record.created_at),
    )


async def get_source_dag(db: AsyncSession, *, source_id: UUID) -> schemas.DAGSchema:
    res = await db.execute(select(models.Schema).where(models.Schema.source_id == source_id))
    schema_record = res.scalar_one_or_none()
    if schema_record is None:
        raise HTTPException(status_code=404, detail="Schema not found for this source")
    return schemas.DAGSchema(**cast(Mapping[str, Any], schema_record.dag_json))


async def get_source_tables(db: AsyncSession, *, source_id: UUID) -> Sequence[schemas.TableSchema]:
    res = await db.execute(select(models.Schema).where(models.Schema.source_id == source_id))
    schema_record = res.scalar_one_or_none()
    if schema_record is None:
        raise HTTPException(status_code=404, detail="Schema not found for this source")
    canonical_schema = schemas.CanonicalSchema(**cast(Mapping[str, Any], schema_record.schema_json))
    return tuple(canonical_schema.tables)


# ---------- Flat preview ----------

def flat_preview(payload: Dict[str, Any]):
    try:
        return preview_flat(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Requests ----------

async def create_request(db: AsyncSession, *, project_id: UUID, request_in: schemas.RequestCreate) -> schemas.Request:
    project = await crud.project.get(db=db, id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    request = await crud.request.create_with_project(db=db, obj_in=request_in, project_id=project_id)
    return request


async def list_requests(db: AsyncSession, *, project_id: UUID, skip: int = 0, limit: int = 100) -> Sequence[schemas.Request]:
    project = await crud.project.get(db=db, id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    reqs = await crud.request.get_by_project(db, project_id=project_id, skip=skip, limit=limit)
    return tuple(reqs)


async def get_request(db: AsyncSession, *, project_id: UUID, request_id: UUID) -> schemas.Request:
    project = await crud.project.get(db=db, id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    request = await crud.request.get(db=db, id=request_id)
    if request is None or request.project_id != project_id:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


async def estimate_request(db: AsyncSession, *, project_id: UUID, request_id: UUID) -> Dict[str, Any]:
    """Estimate size/time for a request.

    Fixes: Previously relied on string casting of enum producing values like
    'RequestType.FLAT' causing unsupported type errors. Now compare enum directly.
    """
    project = await crud.project.get(db=db, id=project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    req = await crud.request.get(db=db, id=request_id)
    if req is None or req.project_id != project_id:
        raise HTTPException(status_code=404, detail="Request not found")
    params = req.params_json or {}
    schema = params.get("schema") or params.get("config")
    if not schema:
        raise HTTPException(status_code=400, detail="Missing schema in request params_json")
    rows_per_table = params.get("rows_per_table", {})
    if req.type == RequestType.RELATIONAL:
        return estimate_relational(schema, rows_per_table)
    if req.type == RequestType.FLAT:
        total_rows = int(params.get("rows", 0) or 0)
        temp_schema = {"tables": [{"name": "data", "columns": schema.get("fields", [])}]}
        rp = {"data": total_rows}
        return estimate_relational(temp_schema, rp)
    raise HTTPException(status_code=400, detail=f"Unsupported request type for estimate: {req.type}")


async def start_request_job(
    db: AsyncSession,
    *,
    request_id: UUID,
    get_queue_fn: Optional[Callable[[str], Any]] = None,
) -> schemas.Request:
    req = await crud.request.get(db=db, id=request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")

    rtype = getattr(req, "type", None)
    params = req.params_json or {}
    priority = "default"
    if isinstance(params, dict):
        priority = str(params.get("priority", "default")).lower()
        if priority not in {"low", "default", "high"}:
            priority = "default"

    # Allow tests to monkeypatch queue getter from endpoint module by accepting an override
    queue_getter = get_queue_fn or get_queue
    q = cast(Any, queue_getter(priority))
    if rtype == RequestType.FLAT:
        job = q.enqueue(
            run_flat_job,
            str(request_id),
            meta={"request_id": str(request_id)},
            retry=Retry(max=3),
        )
    elif rtype == RequestType.RELATIONAL:
        job = q.enqueue(
            run_relational_job,
            str(request_id),
            meta={"request_id": str(request_id)},
            retry=Retry(max=3),
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported request type for start")

    job_id = job.get_id()
    updated_params: Dict[str, Any] = {}
    if isinstance(params, dict):
        updated_params = {**params}
    updated_params["job_id"] = job_id
    updated_params["queue"] = priority
    await crud.request.update(db=db, db_obj=req, obj_in={"params_json": updated_params})

    try:
        if REQUESTS_STARTED is not None:
            typ = "flat" if rtype == RequestType.FLAT else ("relational" if rtype == RequestType.RELATIONAL else str(rtype))
            REQUESTS_STARTED.labels(type=typ).inc()
    except Exception:
        pass

    return await crud.request.get(db=db, id=request_id)


# ---------- Artifacts ----------

async def list_artifacts(db: AsyncSession, *, request_id: UUID) -> Sequence[schemas.Artifact]:
    req = await crud.request.get(db=db, id=request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    arts = await crud.artifact.get_by_request(db, request_id=request_id)
    return tuple(arts)


async def get_artifact(db: AsyncSession, *, request_id: UUID, artifact_id: UUID) -> schemas.Artifact:
    req = await crud.request.get(db=db, id=request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    artifact = await crud.artifact.get(db=db, id=artifact_id)
    if artifact is None or artifact.request_id != request_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


async def sign_artifact(db: AsyncSession, *, request_id: UUID, artifact_id: UUID, expires: int = 3600) -> Dict[str, Any]:
    # Delegate to storage module service for URL signing to centralize logic
    return await storage_sign_artifact(db, request_id=request_id, artifact_id=artifact_id, expires=expires)


# ---------- Validation ----------

def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        rules_norm = parse_rules(payload)
        data_sample = payload.get("data_sample", {})
        data_final = payload.get("data_final", {})
        max_violations = int(payload.get("max_violations", 10))
        report = validate_rules(rules_norm, data_sample, data_final, max_violations)
        return {"rules": rules_norm, "report": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


__all__ = [
    # Sources
    "list_sources",
    "upload_source",
    "get_source_schema",
    "get_source_dag",
    "get_source_tables",
    # Flat
    "flat_preview",
    # Requests
    "create_request",
    "list_requests",
    "get_request",
    "estimate_request",
    "start_request_job",
    # Artifacts
    "list_artifacts",
    "get_artifact",
    "sign_artifact",
    # Validation
    "validate_payload",
]

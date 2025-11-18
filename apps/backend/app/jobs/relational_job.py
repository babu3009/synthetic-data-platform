from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session
from rq import get_current_job  # type: ignore

from app.db.session import SessionLocal
from app.db.models import Request, RequestStatus, RequestType, Artifact, ArtifactFormat, Project
from app.services.relational import generate_to_artifacts
from app.services.storage import get_storage
from app.services.report import create_html_report
from app.services.notify import post_run_status
from app.observability import get_tracer, REQUESTS_STARTED, REQUESTS_COMPLETED, REQUESTS_FAILED

logger = logging.getLogger(__name__)


def run_relational_job(request_id: str) -> None:
    session: Session = SessionLocal()
    try:
        tracer = get_tracer(__name__)
        logger.info(f"Starting relational job for request {request_id}")
        
        with tracer.start_as_current_span("relational_job"):
            rid = UUID(request_id)
            req: Request | None = session.get(Request, rid)
            if not req:
                logger.warning(f"Request {request_id} not found")
                return
            
            req_type = getattr(req, "type", None)
            # Handle both enum objects and string values
            if isinstance(req_type, str):
                req_type_str = req_type
            else:
                req_type_str = req_type.value if hasattr(req_type, 'value') else str(req_type)
            
            logger.info(f"Request {request_id} type: '{req_type_str}' (comparing to '{RequestType.RELATIONAL.value}')")
            if req_type_str != RequestType.RELATIONAL.value:
                logger.warning(f"Request {request_id} is not relational type. Type is: '{req_type_str}'")
                return

            now = datetime.now(timezone.utc)
            # Use setattr to avoid static type checker complaints on SQLAlchemy instrumented attributes
            logger.info(f"Setting request {request_id} status to RUNNING")
            setattr(req, "status", RequestStatus.RUNNING.value)
            setattr(req, "started_at", now)
            session.add(req)
            session.commit()
            session.refresh(req)
            logger.info(f"Request {request_id} status updated to RUNNING in database")

            # Notify RUNNING
            proj = session.get(Project, getattr(req, "project_id", None))
            webhook = getattr(proj, "webhook_run_status_url", None) if proj else None
            job = get_current_job()
            if job is not None:
                job.meta["status"] = "running"
                job.meta["progress"] = 0
                job.save_meta()
            post_run_status(
                webhook,
                {
                    "project_id": str(getattr(req, "project_id", "")),
                    "request_id": str(request_id),
                    "status": "running",
                    "progress": 0,
                },
            )

            params: Dict[str, Any] = {}
            raw = getattr(req, "params_json", None)
            if isinstance(raw, dict):
                params = raw
            schema = params.get("schema") or params.get("config")
            if not schema:
                raise ValueError("Missing schema in request params_json")
            
            # Extract rows_per_table from params or from schema table definitions
            rows_per_table: Dict[str, int] = params.get("rows_per_table", {})
            if not rows_per_table and isinstance(schema, dict):
                # Extract from table definitions if not provided
                tables = schema.get("tables", [])
                for table in tables:
                    tname = table.get("name")
                    if tname:
                        # Check for rowTarget field (from frontend)
                        row_target = table.get("rowTarget")
                        if isinstance(row_target, dict) and row_target.get("type") == "absolute":
                            rows_per_table[tname] = int(row_target.get("value", 1000))
                        elif table.get("rows"):
                            rows_per_table[tname] = int(table.get("rows"))
                        else:
                            # Default to 1000 rows if not specified
                            rows_per_table[tname] = 1000
            
            # Get formats from outputs.formats or fall back to params.formats or default
            outputs: Dict[str, Any] = params.get("outputs", {}) if isinstance(params.get("outputs"), dict) else {}
            formats: List[str] = outputs.get("formats") or params.get("formats", [ArtifactFormat.CSV.value, ArtifactFormat.PARQUET.value, ArtifactFormat.XLSX.value])
            
            seed: int = int(params.get("seed", req.seed or 0))
            chunk_size: int = int(params.get("chunk_size", 50_000))
            db_writeback = outputs.get("db") if isinstance(outputs.get("db"), dict) else None
            kafka_publish = outputs.get("kafka") if isinstance(outputs.get("kafka"), dict) else None

            # Use absolute path for tmp directory
            backend_root = Path(__file__).resolve().parents[2]  # Go up from jobs/ to backend/
            tmp_dir = backend_root / "storage" / "tmp" / request_id
            tmp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using temporary directory: {tmp_dir}")

            paths_by_table, report = generate_to_artifacts(
                target_dir=tmp_dir,
                schema=schema,
                rows_per_table=rows_per_table,
                formats=[f.lower() for f in formats],
                seed=seed,
                chunk_size=chunk_size,
                db_writeback=db_writeback,
                kafka_publish=kafka_publish,
            )

            storage = get_storage()
            # Upload per-table artifacts and record
            uploaded_artifacts: List[Dict[str, Any]] = []
            recorded: set[str] = set()
            for tname, fmap in paths_by_table.items():
                for fmt, p in fmap.items():
                    # Only upload each workbook path once (xlsx shared)
                    if fmt == "xlsx":
                        if str(p) in recorded:
                            continue
                        recorded.add(str(p))
                        object_name = f"requests/{request_id}/data.xlsx"
                    else:
                        object_name = f"requests/{request_id}/{tname}.{fmt}"
                    stored = storage.put_file(p, object_name)
                    art = Artifact(
                        request_id=rid,
                        format=ArtifactFormat(fmt),
                        storage_uri=stored.uri,
                        size_bytes=stored.size,
                    )
                    session.add(art)
                    uploaded_artifacts.append({
                        "table": tname,
                        "format": fmt,
                        "uri": stored.uri,
                        "size": stored.size,
                    })

            # Midway progress
            if job is not None:
                job.meta["progress"] = 90
                job.save_meta()
            
            # Update params_json with progress
            try:
                current_params = dict(params)
                current_params["progress"] = 90
                setattr(req, "params_json", current_params)
                session.add(req)
                session.commit()
            except Exception:
                pass  # Best effort
            
            post_run_status(
                webhook,
                {
                    "project_id": str(getattr(req, "project_id", "")),
                    "request_id": str(request_id),
                    "status": "running",
                    "progress": 90,
                },
            )

            # Generate and upload HTML report; persist under params_json["relational_report"],
            # and record an Artifact with format=html
            try:
                # Prepare a minimal summary for the report
                summary: Dict[str, Any] = {
                    "tables": list(paths_by_table.keys()),
                    "rows_per_table": rows_per_table,
                    "report": report,
                }
                # Try to include schema tables if available (for FK graph)
                schema_obj = schema if isinstance(schema, dict) else {"tables": []}
                report_path = create_html_report(
                    request_id=str(request_id),
                    target_dir=tmp_dir,
                    schema=schema_obj,
                    summary=summary,
                    artifacts=uploaded_artifacts,
                    samples=None,
                )
                stored_report = storage.put_file(report_path, f"requests/{request_id}/report.html")
                report_art = Artifact(
                    request_id=rid,
                    format=ArtifactFormat.HTML,
                    storage_uri=stored_report.uri,
                    size_bytes=stored_report.size,
                )
                session.add(report_art)
            except Exception:
                # Best-effort; continue without blocking completion
                pass

            # Persist report under params_json["relational_report"] and progress
            params_out = dict(params)
            params_out["relational_report"] = report
            params_out["progress"] = 100  # Persist final progress
            setattr(req, "params_json", params_out)
            logger.info(f"Setting request {request_id} status to COMPLETED")
            setattr(req, "status", RequestStatus.COMPLETED.value)
            setattr(req, "finished_at", datetime.now(timezone.utc))
            session.add(req)
            session.commit()
            session.refresh(req)
            logger.info(f"Request {request_id} status updated to COMPLETED in database. Final status: {req.status}")
            logger.info(f"Request {request_id} finished_at: {req.finished_at}")

            # Notify COMPLETED
            if job is not None:
                job.meta["status"] = "completed"
                job.meta["progress"] = 100
                job.save_meta()
            post_run_status(
                webhook,
                {
                    "project_id": str(getattr(req, "project_id", "")),
                    "request_id": str(request_id),
                    "status": "completed",
                    "progress": 100,
                },
            )

        # Metrics: completed
        try:
            if REQUESTS_COMPLETED is not None:
                REQUESTS_COMPLETED.labels(type="relational").inc()
        except Exception:
            pass

    except Exception as e:  # pragma: no cover
        import traceback
        logger.error(f"Request {request_id} failed with error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            req2 = session.get(Request, UUID(request_id))
            if req2:
                params2: Dict[str, Any] = {}
                raw2 = getattr(req2, "params_json", None)
                if isinstance(raw2, dict):
                    params2 = dict(raw2)
                params2["error"] = str(e)
                setattr(req2, "params_json", params2)
                setattr(req2, "error_message", str(e))
                setattr(req2, "error_traceback", traceback.format_exc())
                logger.info(f"Setting request {request_id} status to FAILED")
                setattr(req2, "status", RequestStatus.FAILED.value)
                setattr(req2, "finished_at", datetime.now(timezone.utc))
                session.add(req2)
                session.commit()
                session.refresh(req2)
                logger.info(f"Request {request_id} status updated to FAILED in database. Final status: {req2.status}")
                # Notify FAILED
                proj = session.get(Project, getattr(req2, "project_id", None))
                webhook = getattr(proj, "webhook_run_status_url", None) if proj else None
                job = get_current_job()
                if job is not None:
                    job.meta["status"] = "failed"
                    job.save_meta()
                post_run_status(
                    webhook,
                    {
                        "project_id": str(getattr(req2, "project_id", "")),
                        "request_id": str(request_id),
                        "status": "failed",
                        "error": str(e),
                    },
                )
            # Metrics: failed
            try:
                if REQUESTS_FAILED is not None:
                    REQUESTS_FAILED.labels(type="relational").inc()
            except Exception:
                pass
        finally:
            # Re-raise to allow RQ Retry policies to apply
            raise
    finally:
        session.close()

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from typing import Any, Dict, List
from sqlalchemy.orm import Session
from rq import get_current_job  # type: ignore

from app.db.session import SessionLocal
from app.db.models import Request, RequestStatus, RequestType, Artifact, ArtifactFormat, Project
from app.services.flat import generate_to_artifacts
from app.services.storage import get_storage
from app.services.notify import post_run_status
from app.observability import get_tracer, REQUESTS_COMPLETED, REQUESTS_FAILED


def run_flat_job(request_id: str) -> None:
    """
    RQ worker job: generate flat artifacts for the given request id.

    Transitions:
    - PENDING -> RUNNING -> COMPLETED
    - PENDING/RUNNING -> FAILED on exception
    """
    # Use sync session within RQ worker
    session: Session = SessionLocal()
    try:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("flat_job"):
        rid = UUID(request_id)
        req: Request | None = session.get(Request, rid)
        if not req:
            return
        # Avoid InstrumentedAttribute comparison issues
        if str(getattr(req, "type", "")) != RequestType.FLAT:
            return

        now = datetime.now(timezone.utc)
        req_obj: Any = req
        req_obj.status = RequestStatus.RUNNING
        req_obj.started_at = now
        session.add(req_obj)
        session.commit()
        session.refresh(req_obj)

        # Notify RUNNING
        proj = session.get(Project, getattr(req_obj, "project_id", None))
        webhook = getattr(proj, "webhook_run_status_url", None) if proj else None
        job = get_current_job()
        if job is not None:
            job.meta["status"] = "running"
            job.meta["progress"] = 0
            job.save_meta()
        post_run_status(
            webhook,
            {
                "project_id": str(getattr(req_obj, "project_id", "")),
                "request_id": request_id,
                "status": "running",
                "progress": 0,
            },
        )

        params: Dict[str, Any] = {}
        raw_params = getattr(req_obj, "params_json", None)
        if isinstance(raw_params, dict):
            params = raw_params
        schema = params.get("schema") or params.get("config")
        if not schema:
            raise ValueError("Missing schema in request params_json")
        total_rows = int(params.get("rows", 1000))
        formats: List[str] = params.get("formats", [ArtifactFormat.CSV.value])
        chunk_size = int(params.get("chunk_size", 50_000))
        outputs: Dict[str, Any] = params.get("outputs", {}) if isinstance(params.get("outputs"), dict) else {}
        db_writeback = outputs.get("db") if isinstance(outputs.get("db"), dict) else None
        kafka_publish = outputs.get("kafka") if isinstance(outputs.get("kafka"), dict) else None

        tmp_dir = Path("storage/tmp") / request_id
        tmp_dir.mkdir(parents=True, exist_ok=True)

        paths, stats = generate_to_artifacts(
            target_dir=tmp_dir,
            schema=schema,
            total_rows=total_rows,
            formats=formats,
            chunk_size=chunk_size,
            db_writeback=db_writeback,
            kafka_publish=kafka_publish,
        )

        # Midway progress
        if job is not None:
            job.meta["progress"] = 90
            job.save_meta()
        post_run_status(
            webhook,
            {
                "project_id": str(getattr(req_obj, "project_id", "")),
                "request_id": request_id,
                "status": "running",
                "progress": 90,
            },
        )

        storage = get_storage()
        for p in paths:
            object_name = f"requests/{request_id}/{p.name}"
            stored = storage.put_file(p, object_name)
            fmt = ArtifactFormat(p.suffix.replace('.', '').lower())
            art = Artifact(
                request_id=rid,
                format=fmt,
                storage_uri=stored.uri,
                size_bytes=stored.size,
            )
            session.add(art)

    # persist stats into params_json["stats"]
        new_params = dict(params)
        new_params["stats"] = stats
        req_obj.params_json = new_params
        req_obj.status = RequestStatus.COMPLETED
        req_obj.finished_at = datetime.now(timezone.utc)
        session.add(req_obj)
        session.commit()

        # Notify COMPLETED
        if job is not None:
            job.meta["status"] = "completed"
            job.meta["progress"] = 100
            job.save_meta()
        post_run_status(
            webhook,
            {
                "project_id": str(getattr(req_obj, "project_id", "")),
                "request_id": request_id,
                "status": "completed",
                "progress": 100,
            },
        )

        # Metrics: completed
        try:
            if REQUESTS_COMPLETED is not None:
                REQUESTS_COMPLETED.labels(type="flat").inc()
        except Exception:
            pass

    except Exception as e:  # pragma: no cover
        try:
            req2 = session.get(Request, UUID(request_id))
            if req2:
                req2_obj: Any = req2
                params2: Dict[str, Any] = {}
                raw = getattr(req2_obj, "params_json", None)
                if isinstance(raw, dict):
                    params2 = dict(raw)
                params2["error"] = str(e)
                req2_obj.params_json = params2
                req2_obj.status = RequestStatus.FAILED
                req2_obj.finished_at = datetime.now(timezone.utc)
                session.add(req2_obj)
                session.commit()
                # Notify FAILED
                proj = session.get(Project, getattr(req2_obj, "project_id", None))
                webhook = getattr(proj, "webhook_run_status_url", None) if proj else None
                job = get_current_job()
                if job is not None:
                    job.meta["status"] = "failed"
                    job.save_meta()
                post_run_status(
                    webhook,
                    {
                        "project_id": str(getattr(req2_obj, "project_id", "")),
                        "request_id": request_id,
                        "status": "failed",
                        "error": str(e),
                    },
                )
            # Metrics: failed
            try:
                if REQUESTS_FAILED is not None:
                    REQUESTS_FAILED.labels(type="flat").inc()
            except Exception:
                pass
        finally:
            # Re-raise to allow RQ Retry policies to apply
            raise
    finally:
        session.close()

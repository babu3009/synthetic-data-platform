from __future__ import annotations

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
from app.services.notify import post_run_status


def run_relational_job(request_id: str) -> None:
    session: Session = SessionLocal()
    try:
        rid = UUID(request_id)
        req: Request | None = session.get(Request, rid)
        if not req:
            return
        if str(getattr(req, "type", "")) != RequestType.RELATIONAL:
            return

        now = datetime.now(timezone.utc)
        # Use setattr to avoid static type checker complaints on SQLAlchemy instrumented attributes
        setattr(req, "status", RequestStatus.RUNNING)
        setattr(req, "started_at", now)
        session.add(req)
        session.commit()
        session.refresh(req)

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
        rows_per_table: Dict[str, int] = params.get("rows_per_table", {})
        formats: List[str] = params.get("formats", [ArtifactFormat.CSV.value, ArtifactFormat.PARQUET.value, ArtifactFormat.XLSX.value])
        seed: int = int(params.get("seed", req.seed or 0))
        chunk_size: int = int(params.get("chunk_size", 50_000))
        outputs: Dict[str, Any] = params.get("outputs", {}) if isinstance(params.get("outputs"), dict) else {}
        db_writeback = outputs.get("db") if isinstance(outputs.get("db"), dict) else None
        kafka_publish = outputs.get("kafka") if isinstance(outputs.get("kafka"), dict) else None

        tmp_dir = Path("storage/tmp") / request_id
        tmp_dir.mkdir(parents=True, exist_ok=True)

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

        # Midway progress
        if job is not None:
            job.meta["progress"] = 90
            job.save_meta()
        post_run_status(
            webhook,
            {
                "project_id": str(getattr(req, "project_id", "")),
                "request_id": str(request_id),
                "status": "running",
                "progress": 90,
            },
        )

        # Persist report under params_json["relational_report"]
        params_out = dict(params)
        params_out["relational_report"] = report
        setattr(req, "params_json", params_out)
        setattr(req, "status", RequestStatus.COMPLETED)
        setattr(req, "finished_at", datetime.now(timezone.utc))
        session.add(req)
        session.commit()

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

    except Exception as e:  # pragma: no cover
        try:
            req2 = session.get(Request, UUID(request_id))
            if req2:
                params2: Dict[str, Any] = {}
                raw2 = getattr(req2, "params_json", None)
                if isinstance(raw2, dict):
                    params2 = dict(raw2)
                params2["error"] = str(e)
                setattr(req2, "params_json", params2)
                setattr(req2, "status", RequestStatus.FAILED)
                setattr(req2, "finished_at", datetime.now(timezone.utc))
                session.add(req2)
                session.commit()
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
        finally:
            # Re-raise to allow RQ Retry policies to apply
            raise
    finally:
        session.close()

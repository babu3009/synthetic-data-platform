from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Project, Request, Artifact
from app.services.storage import get_storage


def _object_name_from_uri(uri: str) -> str:
    if uri.startswith("s3://"):
        try:
            return uri.split("/", 3)[3]
        except Exception:
            return uri
    if "/requests/" in uri:
        return uri.split("/requests/")[-1]
    return uri


def cleanup_expired_artifacts_with_session(session: Session) -> dict:
    """Cleanup artifacts older than per-project TTL.

    Returns summary dict with counts.
    """
    deleted = 0
    examined = 0
    storage = get_storage()

    # Load projects with TTL
    projects = session.execute(
        select(Project).where(Project.artifact_ttl_days.isnot(None))
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for proj in projects:
        ttl_days = getattr(proj, "artifact_ttl_days", None)
        # If TTL is None, skip. If 0, delete immediately (no retention)
        if ttl_days is None:
            continue
        days = max(int(ttl_days), 0)
        cutoff = now - timedelta(days=days)

        # Find artifacts for this project's requests older than cutoff
        # Join requests -> artifacts
        reqs = session.execute(
            select(Request.id).where(Request.project_id == proj.id)
        ).scalars().all()
        if not reqs:
            continue
        arts = session.execute(
            select(Artifact).where(
                and_(Artifact.request_id.in_(reqs), Artifact.created_at < cutoff)
            )
        ).scalars().all()

        for art in arts:
            examined += 1
            uri = str(getattr(art, "storage_uri", ""))
            object_name = _object_name_from_uri(uri)
            try:
                storage.delete_object(object_name)
            except Exception:
                # Continue even if storage delete fails
                pass
            # Delete DB row
            session.delete(art)
            deleted += 1
        session.commit()

    return {"examined": examined, "deleted": deleted}


def cleanup_expired_artifacts() -> dict:
    """Entry point that manages its own session."""
    session: Session = SessionLocal()
    try:
        return cleanup_expired_artifacts_with_session(session)
    finally:
        session.close()

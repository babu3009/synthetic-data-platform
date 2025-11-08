"""Tests for artifact cleanup job logic.

Focus on unit-testing `cleanup_expired_artifacts_with_session` without real storage
dependencies by mocking `get_storage`. We construct in-memory objects via a transient
SQLite database bound to the same SQLAlchemy models to validate cutoff logic.

Edge cases covered:
1. Project with `artifact_ttl_days=None` is skipped.
2. TTL=0 removes all artifacts regardless of age.
3. TTL > 0 only deletes artifacts older than cutoff.
4. Storage delete failures are swallowed and DB row still removed.

NOTE: This test uses a dedicated engine to avoid coupling to production connection
settings and runs quickly (< 1s).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import patch, MagicMock

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def _import_cleanup():
    # Import cleanup after env is set so that any sessions/models use the test schema
    from app.jobs.cleanup import cleanup_expired_artifacts_with_session  # type: ignore
    return cleanup_expired_artifacts_with_session


def _import_models():
    # Ensure SQLite-friendly schema during tests
    # This must occur before importing models/Base so that SCHEMA_NAME resolves to 'main'.
    os.environ.setdefault('TESTING_DB_SCHEMA', 'main')
    from app.db.models import (  # type: ignore
        Base,
        Project,
        Request,
        Artifact,
        ArtifactFormat,
        RequestType,
        RequestStatus,
    )
    return Base, Project, Request, Artifact, ArtifactFormat, RequestType, RequestStatus


def _make_session():
    Base, *_ = _import_models()
    engine = create_engine("sqlite:///:memory:", echo=False)
    # SQLite does not support schemas; strip schema from metadata and tables
    try:
        Base.metadata.schema = None
        for t in Base.metadata.tables.values():
            t.schema = None
    except Exception:
        pass
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_cleanup_ttl_logic_and_storage_failure():
    # Import models now that TESTING_DB_SCHEMA is set
    Base, Project, Request, Artifact, ArtifactFormat, RequestType, RequestStatus = _import_models()
    session = _make_session()
    now = _utc_now()

    # Projects: skipped (None), immediate delete (0 days), TTL=2 days
    p_skip = Project(name="skip", owner="o", tags={}, artifact_ttl_days=None)
    p_zero = Project(name="zero", owner="o", tags={}, artifact_ttl_days=0)
    p_two = Project(name="two", owner="o", tags={}, artifact_ttl_days=2)
    session.add_all([p_skip, p_zero, p_two])
    session.commit()

    # Requests per project
    r_zero = Request(project_id=p_zero.id, type=RequestType.RELATIONAL, status=RequestStatus.COMPLETED)
    r_two = Request(project_id=p_two.id, type=RequestType.RELATIONAL, status=RequestStatus.COMPLETED)
    session.add_all([r_zero, r_two])
    session.commit()

    # Artifacts: For TTL=0 project (all should delete)
    a0_new = Artifact(request_id=r_zero.id, format=ArtifactFormat.CSV, storage_uri="s3://bucket/requests/a0_new.csv")
    a0_old = Artifact(request_id=r_zero.id, format=ArtifactFormat.CSV, storage_uri="s3://bucket/requests/a0_old.csv")

    # For TTL=2 days project: one old (>2d), one recent (<2d)
    old_time = now - timedelta(days=3)
    recent_time = now - timedelta(hours=12)
    a2_old = Artifact(request_id=r_two.id, format=ArtifactFormat.CSV, storage_uri="s3://bucket/requests/a2_old.csv")
    a2_recent = Artifact(request_id=r_two.id, format=ArtifactFormat.CSV, storage_uri="s3://bucket/requests/a2_recent.csv")

    # Manually set created_at timestamps (SQLite doesn't apply server_default immediately)
    for art, ts in [
        (a0_new, now),
        (a0_old, now - timedelta(days=10)),
        (a2_old, old_time),
        (a2_recent, recent_time),
    ]:
        art.created_at = ts

    session.add_all([a0_new, a0_old, a2_old, a2_recent])
    session.commit()

    deleted_objects: List[str] = []

    class FakeStorage:
        def delete_object(self, name: str):  # pragma: no cover - simple mock
            deleted_objects.append(name)
            if name.endswith("a0_old.csv"):
                raise RuntimeError("Simulated delete failure")

    with patch("app.jobs.cleanup.get_storage", return_value=FakeStorage()):
        cleanup_fn = _import_cleanup()
        summary = cleanup_fn(session)

    # TTL=0 project: both artifacts removed despite failure swallowing
    assert {"requests/a0_new.csv", "requests/a0_old.csv"}.issubset(set(deleted_objects))
    # TTL=2 days project: only old artifact deleted
    assert "requests/a2_old.csv" in deleted_objects
    assert "requests/a2_recent.csv" not in deleted_objects

    # Database should no longer contain deleted artifacts
    remaining = session.query(Artifact).all()
    remaining_uris = {a.storage_uri for a in remaining}
    assert "s3://bucket/requests/a0_new.csv" not in remaining_uris
    assert "s3://bucket/requests/a0_old.csv" not in remaining_uris
    assert "s3://bucket/requests/a2_old.csv" not in remaining_uris
    assert "s3://bucket/requests/a2_recent.csv" in remaining_uris

    # Summary counts: examined artifacts = 3 (skips recent one), deleted = 3
    assert summary["deleted"] == 3
    assert summary["examined"] == 3

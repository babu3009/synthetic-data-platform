from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from app.core.config import settings
from sqlalchemy.orm import sessionmaker

from app import crud, schemas
from app.api.api_v1.endpoints import flat as flat_endpoint
from app.db.models import ArtifactFormat, RequestType, RequestStatus, Project, Request, Artifact
from app.db.base import Base
from app.jobs.cleanup import cleanup_expired_artifacts_with_session


class FakeJob:
    def __init__(self):
        self._id = "job-123"
        self.args = None
        self.meta = None
        self.retry = None

    def get_id(self):
        return self._id


class FakeQueue:
    def __init__(self, name: str):
        self.name = name
        self.last_enqueued = None

    def enqueue(self, func, *args, **kwargs):
        self.last_enqueued = {"func": func, "args": args, "kwargs": kwargs}
        return FakeJob()


@pytest_asyncio.fixture
async def project(async_client: AsyncClient) -> dict:
    payload = {"name": "WebhookProj", "owner": "me@example.com", "tags": []}
    r = await async_client.post("/api/v1/projects/", json=payload)
    assert r.status_code == 200
    return r.json()


@pytest.mark.asyncio
async def test_register_run_status_webhook(async_client: AsyncClient, project):
    body = {"project_id": project["id"], "url": "http://localhost/callback"}
    r = await async_client.post("/api/v1/webhooks/run-status", json=body)
    assert r.status_code == 200
    pr = await async_client.get(f"/api/v1/projects/{project['id']}")
    assert pr.status_code == 200
    assert pr.json()["webhook_run_status_url"] == "http://localhost/callback"


@pytest.mark.asyncio
async def test_start_uses_priority_queue(async_client: AsyncClient, db_session: AsyncSession, project, monkeypatch):
    # Create request with priority "high"
    req = await crud.request.create_with_project(
        db=db_session,
        obj_in=schemas.RequestCreate(type=RequestType.FLAT, seed=1, params_json={"priority": "high"}),
        project_id=UUID(project["id"]),
    )

    # Monkeypatch queue getter
    captured = {}

    def fake_get_queue(name: str = "default"):
        q = FakeQueue(name)
        captured["queue"] = q
        return q

    monkeypatch.setattr(flat_endpoint, "get_queue", fake_get_queue)

    # Start the request
    r = await async_client.post(f"/api/v1/requests/{req.id}:start")
    assert r.status_code == 200
    assert captured["queue"].name == "high"


@pytest.mark.asyncio
async def test_start_sets_retry_policy(async_client: AsyncClient, db_session: AsyncSession, project, monkeypatch):
    # Create request with default priority
    req = await crud.request.create_with_project(
        db=db_session,
        obj_in=schemas.RequestCreate(type=RequestType.RELATIONAL, seed=1, params_json={}),
        project_id=UUID(project["id"]),
    )

    captured = {}

    def fake_get_queue(name: str = "default"):
        q = FakeQueue(name)
        captured["queue"] = q
        return q

    monkeypatch.setattr(flat_endpoint, "get_queue", fake_get_queue)

    r = await async_client.post(f"/api/v1/requests/{req.id}:start")
    assert r.status_code == 200
    enq = captured["queue"].last_enqueued
    assert enq is not None
    # Ensure Retry is set with max >= 1
    retry_obj = enq["kwargs"].get("retry")
    assert retry_obj is not None
    assert getattr(retry_obj, "max", 0) >= 1


@pytest.mark.asyncio
async def test_sign_artifact_url(async_client: AsyncClient, db_session: AsyncSession):
    # Create project, request, artifact
    project = await crud.project.create(
        db=db_session, obj_in=schemas.ProjectCreate(name="P", owner="o", tags=[])
    )
    request = await crud.request.create_with_project(
        db=db_session,
        obj_in=schemas.RequestCreate(type=RequestType.FLAT, seed=42, params_json={}),
        project_id=project.id,
    )
    artifact = await crud.artifact.create_with_request(
        db=db_session,
        obj_in=schemas.ArtifactCreate(
            format=ArtifactFormat.CSV, storage_uri="s3://bucket/requests/key/file.csv", size_bytes=1
        ),
        request_id=request.id,
    )
    r = await async_client.get(f"/api/v1/requests/{request.id}/artifacts/{artifact.id}:sign?expires=123")
    assert r.status_code == 200
    data = r.json()
    assert "url" in data and isinstance(data["url"], str)
    assert data["expires"] == 123


def test_cleanup_expired_artifacts(tmp_path):
    # Use a separate sqlite db file
    db_url = f"sqlite:///{tmp_path}/cleanup.db"
    # Map the Postgres schema to default for SQLite
    engine = create_engine(
        db_url,
        echo=False,
        execution_options={"schema_translate_map": {settings.DB_SCHEMA: None}},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Create project with TTL 0 days (delete immediately)
        proj = Project(name="C", owner="o", tags=[], artifact_ttl_days=0)
        session.add(proj)
        session.commit()

        # Create request and artifact older than 1 day
        req = Request(project_id=proj.id, type=RequestType.FLAT, status=RequestStatus.COMPLETED)
        session.add(req)
        session.commit()

        art = Artifact(
            request_id=req.id,
            format=ArtifactFormat.CSV,
            storage_uri="s3://bucket/requests/old/file.csv",
            size_bytes=1,
        )
        # Manually set created_at to old time
        session.add(art)
        session.commit()
        session.execute(
            Artifact.__table__.update()
            .where(Artifact.id == art.id)
            .values(created_at=datetime.now(timezone.utc) - timedelta(days=10))
        )
        session.commit()

        res = cleanup_expired_artifacts_with_session(session)
        assert isinstance(res, dict)
        # When TTL is 0, everything is considered expired
        assert res["examined"] >= 1
    finally:
        session.close()
        engine.dispose()

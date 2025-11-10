from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.models import RequestType, ArtifactFormat


@pytest.mark.asyncio
async def test_sign_artifact_delegates_to_storage_service(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
):
    # Arrange: create project, request, artifact
    project = await crud.project.create(
        db=db_session, obj_in=schemas.ProjectCreate(name="P2", owner="o2", tags=[])
    )
    request = await crud.request.create_with_project(
        db=db_session,
        obj_in=schemas.RequestCreate(type=RequestType.FLAT, seed=7, params_json={}),
        project_id=project.id,
    )
    artifact = await crud.artifact.create_with_request(
        db=db_session,
        obj_in=schemas.ArtifactCreate(
            format=ArtifactFormat.CSV,
            storage_uri="s3://bucket/requests/key/file2.csv",
            size_bytes=123,
        ),
        request_id=request.id,
    )

    # Capture delegation calls
    calls = {}

    async def fake_storage_sign(db, *, request_id, artifact_id, expires: int = 3600):
        calls["db"] = db
        calls["request_id"] = request_id
        calls["artifact_id"] = artifact_id
        calls["expires"] = expires
        return {"url": "http://signed.example/abc", "expires": expires}

    # Monkeypatch the artifacts endpoint's imported alias (post-wiring now uses storage service directly)
    import app.api.api_v1.endpoints.artifacts as artifacts_endpoint
    monkeypatch.setattr(artifacts_endpoint, "service_sign_artifact", fake_storage_sign)

    # Act: call the public endpoint which uses synth.service.sign_artifact under the hood
    r = await async_client.get(
        f"/api/v1/requests/{request.id}/artifacts/{artifact.id}:sign?expires=999"
    )

    # Assert: endpoint succeeded and delegation occurred with expected args
    assert r.status_code == 200
    data = r.json()
    assert data == {"url": "http://signed.example/abc", "expires": 999}
    assert calls["request_id"] == request.id
    assert calls["artifact_id"] == artifact.id
    assert calls["expires"] == 999

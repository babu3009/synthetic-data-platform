import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app import crud
from app.db.models import ProjectRole


@pytest.mark.anyio
async def test_api_key_scopes_read_project(async_client: httpx.AsyncClient, db_session: AsyncSession):
    # Create a project
    proj = await crud.project.create(db_session, obj_in=type("Obj", (), {
        "model_dump": lambda self=None: {
            "name": "Auth Test",
            "owner": "owner@example.com",
            "tags": [],
        }
    })())

    # Add owner membership
    await crud.project_member.create(db_session, obj_in=type("Obj", (), {
        "model_dump": lambda self=None: {
            "project_id": proj.id,
            "user_sub": "user-1",
            "role": ProjectRole.OWNER,
        }
    })())

    # Create API key with read:project scope
    resp = await async_client.post(
        f"/api/v1/projects/{proj.id}/api-keys/",
        headers={"X-User-Sub": "user-1"},
        json={"name": "read-key", "scopes": ["read:project"]},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    key = data["plaintext_key"]
    assert key

    # Use API key to read project
    r2 = await async_client.get(f"/api/v1/projects/{proj.id}", headers={"X-API-Key": key})
    assert r2.status_code == 200

    # Without scope, should fail
    resp2 = await async_client.post(
        f"/api/v1/projects/{proj.id}/api-keys/",
        headers={"X-User-Sub": "user-1"},
        json={"name": "no-scope", "scopes": []},
    )
    assert resp2.status_code == 201
    key2 = resp2.json()["plaintext_key"]
    r3 = await async_client.get(f"/api/v1/projects/{proj.id}", headers={"X-API-Key": key2})
    assert r3.status_code == 403


@pytest.mark.anyio
async def test_run_request_scope(async_client: httpx.AsyncClient, db_session: AsyncSession):
    # Setup project and membership
    proj = await crud.project.create(db_session, obj_in=type("Obj", (), {
        "model_dump": lambda self=None: {
            "name": "Run Test",
            "owner": "owner@example.com",
            "tags": [],
        }
    })())
    await crud.project_member.create(db_session, obj_in=type("Obj", (), {
        "model_dump": lambda self=None: {
            "project_id": proj.id,
            "user_sub": "owner-user",
            "role": ProjectRole.OWNER,
        }
    })())

    # Create key with run:request
    resp = await async_client.post(
        f"/api/v1/projects/{proj.id}/api-keys/",
        headers={"X-User-Sub": "owner-user"},
        json={"name": "runner", "scopes": ["run:request", "read:project"]},
    )
    assert resp.status_code == 201, resp.text
    api_key = resp.json()["plaintext_key"]

    # Create request under project
    req_resp = await async_client.post(
        f"/api/v1/projects/{proj.id}/requests/",
        headers={"X-API-Key": api_key},
        json={"type": "flat", "status": "pending", "seed": 1, "params_json": {"priority": "low"}},
    )
    # Creating request requires write:project; with only read+run this should be forbidden
    assert req_resp.status_code in (400, 403)

    # Create request as owner
    req_resp2 = await async_client.post(
        f"/api/v1/projects/{proj.id}/requests/",
        headers={"X-User-Sub": "owner-user"},
        json={"type": "flat", "status": "pending", "seed": 1, "params_json": {"priority": "low"}},
    )
    assert req_resp2.status_code == 200
    request_id = req_resp2.json()["id"]

    # Start with run:request scope
    start_resp = await async_client.post(
        f"/api/v1/requests/{request_id}:start",
        headers={"X-API-Key": api_key},
    )
    assert start_resp.status_code == 200

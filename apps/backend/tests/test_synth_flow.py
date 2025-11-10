"""Synth request lifecycle flow tests (Phase 2 module validation).

Exercises create → estimate → start job paths for both flat and relational
request types to lock in current behavior before storage/admin refactors.

Focus:
1. Flat request: params_json schema.fields + rows; estimate produces size keys.
2. Relational request: params_json schema.tables + rows_per_table; estimate aggregates.
3. Start job endpoint injects job_id & queue into params_json via fake RQ queue.
4. Subsequent GET returns updated request with pending status unchanged.

These are minimal, non‑e2e tests (no artifact generation awaited).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas

pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture
async def project(async_client: AsyncClient) -> dict:
    resp = await async_client.post(
        "/api/v1/projects/",
        json={"name": "Synth Flow Project", "owner": "flow@example.com", "tags": ["flow"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_flat_request_lifecycle(async_client: AsyncClient, project: dict):
    project_id = project["id"]
    create_payload = {
        "type": "flat",
        "seed": 111,
        "params_json": {
            "rows": 2500,
            "schema": {
                "fields": [
                    {"name": "id", "provider": {"type": "sequence", "start": 1}},
                    {"name": "color", "provider": {"type": "categorical", "categories": ["red", "green", "blue"]}},
                ]
            },
            "priority": "high",
        },
    }
    resp_create = await async_client.post(
        f"/api/v1/projects/{project_id}/requests/", json=create_payload
    )
    assert resp_create.status_code == 200, resp_create.text
    request_flat = resp_create.json()
    assert request_flat["type"] == "flat"
    req_id = request_flat["id"]

    # Estimate
    resp_est = await async_client.post(
        f"/api/v1/projects/{project_id}/requests/{req_id}:estimate"
    )
    assert resp_est.status_code == 200, resp_est.text
    est = resp_est.json()
    for key in ["total_rows", "bytes_csv_est", "bytes_parquet_est", "seconds_est", "per_table"]:
        assert key in est, f"missing key {key} in estimate response"
    assert est["total_rows"] == 2500

    # Start job (injects job_id & queue)
    resp_start = await async_client.post(f"/api/v1/requests/{req_id}:start")
    assert resp_start.status_code == 200, resp_start.text
    started = resp_start.json()
    assert started["id"] == req_id
    pj = started.get("params_json", {})
    assert pj.get("job_id"), "job_id not injected into params_json"
    assert pj.get("queue") == "high"


async def test_relational_request_lifecycle(async_client: AsyncClient, project: dict):
    project_id = project["id"]
    relational_schema = {
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "pk": True, "provider": {"type": "sequence", "start": 1}},
                    {"name": "name", "provider": {"type": "categorical", "categories": ["Alice", "Bob"]}},
                ],
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "pk": True, "provider": {"type": "sequence", "start": 100}},
                    {"name": "customer_id", "fk": {"to_table": "customers", "to_column": "id"}},
                ],
            },
        ]
    }
    rows_per_table = {"customers": 40, "orders": 120}
    create_payload = {
        "type": "relational",
        "seed": 222,
        "params_json": {
            "schema": relational_schema,
            "rows_per_table": rows_per_table,
        },
    }
    resp_create = await async_client.post(
        f"/api/v1/projects/{project_id}/requests/", json=create_payload
    )
    assert resp_create.status_code == 200, resp_create.text
    req_rel = resp_create.json()
    assert req_rel["type"] == "relational"
    req_id = req_rel["id"]

    resp_est = await async_client.post(
        f"/api/v1/projects/{project_id}/requests/{req_id}:estimate"
    )
    assert resp_est.status_code == 200, resp_est.text
    est = resp_est.json()
    assert est["total_rows"] == sum(rows_per_table.values())
    assert set(est["per_table"].keys()) == set(rows_per_table.keys())

    # Start job
    resp_start = await async_client.post(f"/api/v1/requests/{req_id}:start")
    assert resp_start.status_code == 200, resp_start.text
    started = resp_start.json()
    pj = started.get("params_json", {})
    assert pj.get("job_id"), "job_id not injected for relational request"
    assert pj.get("queue") == "default"  # no priority set

    # Re-fetch to ensure persistence
    resp_get = await async_client.get(
        f"/api/v1/projects/{project_id}/requests/{req_id}"
    )
    assert resp_get.status_code == 200
    refetched = resp_get.json()
    assert refetched["params_json"].get("job_id") == pj.get("job_id")

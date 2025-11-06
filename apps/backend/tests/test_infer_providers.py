import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    p = await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(name="Infer Test", owner="infer@example.com", tags=["infer"]))
    return p


@pytest.mark.asyncio
async def test_infer_providers_project_scoped(async_client: AsyncClient, project):
    payload = {
        "columns": [
            {"table": "customers", "column": "email", "dtype": "varchar", "description": "customer email"},
            {"table": "customers", "column": "first_name", "dtype": "text"},
            {"table": "customers", "column": "phone", "dtype": "varchar"},
            {"table": "orders", "column": "amount_total", "dtype": "numeric"},
            {"table": "orders", "column": "iban", "dtype": "varchar"},
        ]
    }
    # Auth disabled in tests via env; see auth.require_project_scope
    resp = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "suggestions" in data
    sugg = data["suggestions"]
    # Should include entries for our inputs
    cols = {(s["table"], s["column"]) for s in sugg}
    for expected in [("customers","email"),("customers","first_name"),("customers","phone"),("orders","amount_total"),("orders","iban")]:
        assert expected in cols
    # Email should have high confidence
    email_s = next(s for s in sugg if s["table"]=="customers" and s["column"]=="email")
    assert email_s["confidence"] >= 0.9
    # Amount suggestion should be an expression/lognormal-like
    amt_s = next(s for s in sugg if s["table"]=="orders" and s["column"]=="amount_total")
    cfg = amt_s["providerConfig"]
    assert isinstance(cfg, dict) and cfg.get("type") in {"expression","date_range","checksum"}


@pytest.mark.asyncio
async def test_infer_providers_alias(async_client: AsyncClient):
    payload = {
        "columns": [
            {"table": "users", "column": "uuid", "dtype": "uuid"},
            {"table": "users", "column": "url", "dtype": "text"},
        ]
    }
    resp = await async_client.post("/api/v1/infer/providers", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggestions"]) >= 2

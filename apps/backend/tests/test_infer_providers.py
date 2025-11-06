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
    assert "results" in data
    results = data["results"]
    # Map for easy lookup
    rc = {(r["table"], r["column"]): r for r in results}
    for expected in [("customers","email"),("customers","first_name"),("customers","phone"),("orders","amount_total"),("orders","iban")]:
        assert expected in rc
        # Each should have at least one suggestion entry
        assert isinstance(rc[expected]["suggestions"], list) and rc[expected]["suggestions"], f"No suggestions for {expected}"
    # Email should have a heuristic suggestion with high score
    email_sug_list = rc[("customers","email")]["suggestions"]
    top_email = email_sug_list[0]
    assert top_email["score"] >= 0.9
    # Amount suggestion should include expression/lognormal-like provider config in some suggestion
    amt_sug_list = rc[("orders","amount_total")]["suggestions"]
    found_amt = False
    for s in amt_sug_list:
        cfg = s.get("provider_config")
        if isinstance(cfg, dict) and cfg.get("type") in {"expression","date_range","checksum"}:
            found_amt = True
            break
    assert found_amt, "Expected amount_total to have expression/date_range/checksum suggestion"


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
    assert "results" in data
    # Ensure both columns present and have suggestions
    rc = {(r["table"], r["column"]): r for r in data["results"]}
    assert ("users","uuid") in rc and ("users","url") in rc
    assert rc[("users","uuid")]["suggestions"]
    assert rc[("users","url")]["suggestions"]

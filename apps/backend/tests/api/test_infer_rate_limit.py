import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    return await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(name="RL Test", owner="rl@example.com", tags=["rl"]))


@pytest.mark.asyncio
async def test_project_infer_rate_limited(async_client: AsyncClient, db_session: AsyncSession, project, monkeypatch):
    # Patch time to a fixed window and reset limiter
    import app.api.api_v1.endpoints.infer as infer_mod
    infer_mod.reset_rate_limiter()
    base = 1_700_000_000.0
    monkeypatch.setattr(infer_mod.time, "time", lambda: base)

    payload = {
        "columns": [
            {"table": "t", "column": "c", "dtype": "varchar", "description": "d"}
        ]
    }

    url = f"/api/v1/projects/{project.id}/infer/providers"
    # First 60 should pass
    for i in range(60):
        r = await async_client.post(url, json=payload)
        assert r.status_code == 200, f"index={i} body={r.text}"

    # 61st should be rate limited
    r2 = await async_client.post(url, json=payload)
    assert r2.status_code == 429, r2.text

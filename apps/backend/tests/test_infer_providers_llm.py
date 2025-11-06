import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app import crud, schemas
from app.services import providers_infer
from app.services.llm import LLMClientFactory
from app.db import models


class FakeClient:
    async def probe(self):
        return {"ok": True}

class FakeCfg:
    provider_kind = "openai"
    temperature = 0.5


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    p = await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(name="Infer LLM Test", owner="llm@example.com", tags=["infer","llm"]))
    # Create a dummy LLM provider and project setting (enabled)
    # Note: use raw insert to avoid needing specific CRUD helpers
    prov_stmt = insert(models.LLMProvider).values(
        kind=models.LLMProviderKind.OPENAI,
        name="openai-test",
        base_url=None,
        is_enabled=True,
    ).returning(models.LLMProvider.id)
    res = await db_session.execute(prov_stmt)
    provider_id = res.scalar_one()

    setting_stmt = insert(models.ProjectLLMSetting).values(
        project_id=p.id,
        enabled=True,
        provider_id=provider_id,
        model_id=None,
        temperature=0.5,
        top_p=None,
        max_tokens=None,
        guardrails_json={},
    )
    await db_session.execute(setting_stmt)
    await db_session.commit()
    return p


@pytest.mark.asyncio
async def test_infer_providers_llm_enabled(monkeypatch, async_client: AsyncClient, project):
    # Monkeypatch factory to simulate enabled LLM client
    async def fake_get_for_project(db, project_id):
        return (FakeClient(), FakeCfg())
    monkeypatch.setattr(LLMClientFactory, "get_for_project", fake_get_for_project)

    payload = {
        "columns": [
            {"table": "customers", "column": "city", "dtype": "text"},
            {"table": "customers", "column": "email", "dtype": "varchar"},
        ]
    }
    resp = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "results" in data
    city_entry = next(r for r in data["results"] if r["table"]=="customers" and r["column"]=="city")
    email_entry = next(r for r in data["results"] if r["table"]=="customers" and r["column"]=="email")
    # Each should have heuristic + LLM suggestions (2 entries)
    assert len(city_entry["suggestions"]) >= 1
    assert any(s["source"]=="LLM" for s in city_entry["suggestions"]) or any(s["source"]=="LLM" for s in email_entry["suggestions"]) 

@pytest.mark.asyncio
async def test_infer_providers_llm_ranking_tie(monkeypatch, async_client: AsyncClient, project):
    # Monkeypatch factory
    async def fake_get_for_project(db, project_id):
        return (FakeClient(), FakeCfg())
    monkeypatch.setattr(LLMClientFactory, "get_for_project", fake_get_for_project)

    # Monkeypatch _llm_refine to keep same confidence (tie) so ordering preference matters
    def fake_refine(columns, suggestions, cfg):
        # Do not modify confidence; just append reason
        for s in suggestions:
            rs = s.get("reasons") or []
            rs.append("llm:tie")
            s["reasons"] = rs
        return suggestions
    monkeypatch.setattr(providers_infer, "_llm_refine", fake_refine)

    payload = {"columns": [ {"table": "customers", "column": "city", "dtype": "text"} ]}
    resp = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    city_entry = next(r for r in data["results"] if r["table"]=="customers" and r["column"]=="city")
    suggs = city_entry["suggestions"]
    # Expect two suggestions (heuristic + LLM)
    assert len(suggs) == 2
    # LLM should appear before heuristic even if scores equal
    assert suggs[0]["source"] == "LLM"

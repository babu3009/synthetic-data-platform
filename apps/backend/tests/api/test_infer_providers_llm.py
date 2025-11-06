import os
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.models import LLMProvider, LLMProviderKind, ProjectLLMSetting


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    p = await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(name="Infer LLM Test", owner="llm@example.com", tags=["infer","llm"]))
    return p


class DummyClient:
    name = "dummy"
    async def probe(self):
        return True, "ok"


def _patch_factory(monkeypatch, provider_kind: str):
    from app.services.llm.factory import ModelConfig
    async def fake_get_for_project(db, *, project_id):
        cfg = ModelConfig(
            provider_kind=provider_kind,
            provider_name=f"{provider_kind}-prov",
            model_name=None,
            temperature=0.2,
            top_p=None,
            max_tokens=None,
            supports_json=None,
        )
        return DummyClient(), cfg
    import app.services.llm.factory as factory_mod
    monkeypatch.setattr(factory_mod.LLMClientFactory, "get_for_project", staticmethod(fake_get_for_project))


def _patch_llm_refine(monkeypatch, new_confidence: float):
    import app.services.providers_infer as pinf
    def fake_refine(columns, suggestions, cfg):
        # Adjust confidence for all suggestions to a specific LLM-driven value
        # We return a new list so endpoint adds a distinct LLM suggestion alongside heuristic
        refined = []
        for s in suggestions:
            rs = dict(s)
            rs["confidence"] = new_confidence
            refined.append(rs)
        return refined
    monkeypatch.setattr(pinf, "_llm_refine", fake_refine)


@pytest.mark.parametrize("kind", [
    LLMProviderKind.OPENAI.value,
    LLMProviderKind.ANTHROPIC.value,
    LLMProviderKind.OLLAMA.value,
    LLMProviderKind.LMSTUDIO.value,
])
@pytest.mark.asyncio
async def test_infer_llm_enabled_orders_by_score(async_client: AsyncClient, db_session: AsyncSession, project, monkeypatch, kind):
    # Provider and setting enabled
    provider = LLMProvider(kind=LLMProviderKind(kind), name=f"{kind}-prov", is_enabled=True)
    db_session.add(provider)
    await db_session.flush()
    setting = ProjectLLMSetting(project_id=project.id, enabled=True, provider_id=provider.id)
    db_session.add(setting)
    await db_session.commit()

    # Patch factory to return dummy client and cfg for this kind
    _patch_factory(monkeypatch, kind)

    # Case 1: LLM boosts above heuristic -> LLM should rank first
    _patch_llm_refine(monkeypatch, new_confidence=0.99)
    payload = {
        "columns": [
            {"table":"customers","column":"email","dtype":"varchar","description":"email"}
        ]
    }
    resp = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload)
    assert resp.status_code == 200, resp.text
    res = resp.json()["results"][0]
    names = [s["source"] for s in res["suggestions"]]
    # First suggestion should be from LLM when score higher
    assert names[0] == "LLM"

    # Case 2: LLM below heuristic -> heuristic remains first
    _patch_llm_refine(monkeypatch, new_confidence=0.60)
    resp2 = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload)
    assert resp2.status_code == 200, resp2.text
    res2 = resp2.json()["results"][0]
    names2 = [s["source"] for s in res2["suggestions"]]
    assert names2[0] == "heuristic"


@pytest.mark.asyncio
async def test_infer_llm_disabled_uses_heuristic_only(async_client: AsyncClient, db_session: AsyncSession, project, monkeypatch):
    # Provider present but setting disabled
    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-prov", is_enabled=True)
    db_session.add(provider)
    await db_session.flush()
    setting = ProjectLLMSetting(project_id=project.id, enabled=False, provider_id=provider.id)
    db_session.add(setting)
    await db_session.commit()

    # Do NOT patch factory or refine; ensure only heuristic entry exists
    payload = {
        "columns": [
            {"table":"customers","column":"email","dtype":"varchar","description":"email"}
        ]
    }
    resp = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload)
    assert resp.status_code == 200
    suggestions = resp.json()["results"][0]["suggestions"]
    # Should have exactly 1 (heuristic) suggestion
    assert len(suggestions) == 1
    assert suggestions[0]["source"] == "heuristic"

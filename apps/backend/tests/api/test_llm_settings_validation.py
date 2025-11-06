import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.models import LLMProvider, LLMProviderKind, LLMModel


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    return await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(name="LLM Settings Test", owner="u@example.com", tags=["llm"]))


@pytest.mark.asyncio
async def test_put_settings_validates_model_belongs_to_provider(async_client: AsyncClient, db_session: AsyncSession, project):
    # Create two providers and a model under provider A
    prov_a = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-a", is_enabled=True)
    prov_b = LLMProvider(kind=LLMProviderKind.ANTHROPIC, name="anthropic-b", is_enabled=True)
    db_session.add_all([prov_a, prov_b])
    await db_session.flush()
    model_a = LLMModel(provider_id=prov_a.id, name="gpt-4o", display_name="GPT-4o")
    db_session.add(model_a)
    await db_session.commit()

    # Case: model_id without provider_id -> 422
    resp0 = await async_client.put(f"/api/v1/projects/{project.id}/llm-settings/", json={
        "enabled": True,
        "model_id": str(model_a.id)
    })
    assert resp0.status_code == 422

    # Case: mismatched provider/model -> 422
    resp = await async_client.put(f"/api/v1/projects/{project.id}/llm-settings/", json={
        "enabled": True,
        "provider_id": str(prov_b.id),
        "model_id": str(model_a.id)
    })
    assert resp.status_code == 422, resp.text

    # Case: correct pairing -> 200
    resp2 = await async_client.put(f"/api/v1/projects/{project.id}/llm-settings/", json={
        "enabled": True,
        "provider_id": str(prov_a.id),
        "model_id": str(model_a.id),
        "temperature": 0.3
    })
    assert resp2.status_code == 200, resp2.text
    body = resp2.json()
    assert body["provider_id"] == str(prov_a.id)
    assert body["model_id"] == str(model_a.id)

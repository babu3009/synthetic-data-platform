import os
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LLMProvider, LLMProviderKind, Project
from app.utils.crypto import encrypt_json
from app import crud, schemas


class DummyAsyncClient:
    """A minimal dummy httpx.AsyncClient replacement for tests."""
    def __init__(self, timeout=10.0):
        self._timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        class Resp:
            def __init__(self, status_code, json_data):
                self.status_code = status_code
                self._json = json_data
            def json(self):
                return self._json

        # OpenAI models response
        if "/v1/models" in url and "openai" in url:
            return Resp(200, {
                "data": [
                    {"id": "gpt-3.5-turbo"},
                    {"id": "gpt-4o-mini"},
                    {"id": "text-embedding-3-large"},  # should be filtered out by heuristic
                ]
            })

        # Anthropic models response
        if "/v1/models" in url and "anthropic" in url:
            return Resp(200, {
                "data": [
                    {"id": "claude-3-haiku-20240307", "display_name": "Claude 3 Haiku", "context_length": 200000}
                ]
            })

        # Ollama tags
        if url.endswith("/api/tags"):
            return Resp(200, {
                "models": [
                    {"name": "llama3", "model": "llama3:instruct", "details": {"family": "llama3"}}
                ]
            })

        # LM Studio
        if url.endswith("/v1/models"):
            return Resp(200, {
                "data": [
                    {"id": "TheBloke/Mixtral-8x7B-Instruct"}
                ]
            })

        return Resp(404, {})


@pytest.mark.asyncio
async def test_discover_models_openai_upsert(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    # Ensure encryption available
    os.environ.setdefault("LLM_SECRET_KEY", "unit-test-secret-key-please-change")

    # Create a project (needed for audit FK)
    project = await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(
        name="LLM Discover Test",
        owner="owner@example.com",
        tags=["llm"],
    ))

    # Create OpenAI provider
    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-admin", is_enabled=True)
    db_session.add(provider)
    await db_session.flush()

    # Add one existing model to test dedup
    await crud.llm_model.create(db=db_session, obj_in=schemas.LLMModelCreate(
        name="gpt-3.5-turbo",
        display_name="gpt-3.5-turbo",
    ))
    # Attach to provider by setting provider_id
    existing = (await crud.llm_model.get_by_provider(db_session, provider_id=provider.id))
    if not existing:
        # manually set provider for the single created model
        # fetch the latest created model
        models_list = await crud.llm_model.get_by_provider(db_session, provider_id=provider.id)
    
    # Create credentials
    enc = encrypt_json({"api_key": "sk-test-xyz"})
    cred = await crud.llm_credential.create(db=db_session, obj_in=schemas.LLMCredentialUpsert(
        api_key="sk-test-xyz", org_id=None, extra={}
    ))
    # Fix provider_id for created credential
    cred.provider_id = provider.id
    db_session.add(cred)
    await db_session.commit()

    # Monkeypatch httpx.AsyncClient
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    # Call endpoint
    resp = await async_client.post(f"/api/v1/admin/llm/providers/{provider.id}:discover-models", params={"project_id": str(project.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    # We expect at least gpt-3.5-turbo (existing) and gpt-4o-mini (new)
    names = [m["name"] for m in data["models"]]
    assert "gpt-3.5-turbo" in names
    assert any("gpt-4o" in n for n in names)
    # Summary counts present
    assert "added_count" in data and "updated_count" in data and "unchanged_count" in data


@pytest.mark.asyncio
async def test_discover_models_ollama(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    # Create a project
    project = await crud.project.create(db=db_session, obj_in=schemas.ProjectCreate(
        name="LLM Discover Ollama",
        owner="owner@example.com",
        tags=["llm"],
    ))

    # Create Ollama provider
    provider = LLMProvider(kind=LLMProviderKind.OLLAMA, name="ollama-admin", base_url="http://localhost:11434", is_enabled=True)
    db_session.add(provider)
    await db_session.commit()

    # Monkeypatch httpx.AsyncClient
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    resp = await async_client.post(f"/api/v1/admin/llm/providers/{provider.id}:discover-models", params={"project_id": str(project.id)})
    assert resp.status_code == 200
    data = resp.json()
    names = [m["name"] for m in data.get("models", [])]
    assert "llama3:instruct" in names
    assert data.get("added_count", 0) >= 1

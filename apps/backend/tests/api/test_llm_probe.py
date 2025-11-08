import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LLMProvider, LLMProviderKind, LLMCredential
from app.utils.crypto import encrypt_json
from app import crud, schemas


class DummyAsyncClient:
    """A minimal dummy httpx.AsyncClient replacement for probe tests."""

    def __init__(self, timeout=3.0):
        self._timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        class Resp:
            def __init__(self, status_code, json_data=None):
                self.status_code = status_code
                self._json = json_data or {}

            def json(self):
                return self._json

        # OpenAI probe
        if url.endswith("/v1/models") and ("openai" in url or "api.openai.com" in url):
            # Simulate success
            return Resp(200, {"data": [{"id": "gpt-4o-mini"}]})

        # Anthropic probe
        if url.endswith("/v1/models") and ("anthropic" in url or "api.anthropic.com" in url):
            return Resp(200, {"data": [{"id": "claude-3-haiku"}]})

        # Ollama probe
        if url.endswith("/api/tags"):
            return Resp(200, {"models": [{"name": "llama3", "model": "llama3:instruct"}]})

        # LM Studio probe
        if url.endswith("/v1/models"):
            return Resp(200, {"data": [{"id": "TheBloke/Mixtral-8x7B-Instruct"}]})

        return Resp(404, {})


@pytest.mark.asyncio
async def test_probe_disabled_provider(async_client: AsyncClient, db_session: AsyncSession):
    # Create a project (needed for audit FK)
    project = await crud.project.create(
        db=db_session,
        obj_in=schemas.ProjectCreate(name="Probe Disabled Test", owner="owner@example.com", tags=["llm"]),
    )

    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-disabled", is_enabled=False)
    db_session.add(provider)
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/admin/llm/providers/{provider.id}:probe", params={"project_id": str(project.id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "disabled" in data["message"].lower()


@pytest.mark.asyncio
async def test_probe_openai_success(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    os.environ.setdefault("LLM_SECRET_KEY", "unit-test-secret-key-please-change")

    project = await crud.project.create(
        db=db_session,
        obj_in=schemas.ProjectCreate(name="Probe OpenAI Test", owner="owner@example.com", tags=["llm"]),
    )

    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-ok", is_enabled=True)
    db_session.add(provider)
    await db_session.flush()

    # Add credentials so probe doesn't early-exit with missing credentials
    enc = encrypt_json({"api_key": "sk-test-xyz"})
    db_session.add(LLMCredential(provider_id=provider.id, enc_payload_json=enc))
    await db_session.commit()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    resp = await async_client.post(
        f"/api/v1/admin/llm/providers/{provider.id}:probe", params={"project_id": str(project.id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "openai ok" in data["message"].lower()
    assert "latency_ms=" in data["message"]


@pytest.mark.asyncio
async def test_probe_missing_credentials(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    project = await crud.project.create(
        db=db_session,
        obj_in=schemas.ProjectCreate(name="Probe Missing Creds", owner="owner@example.com", tags=["llm"]),
    )

    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-nocreds", is_enabled=True)
    db_session.add(provider)
    await db_session.commit()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    resp = await async_client.post(
        f"/api/v1/admin/llm/providers/{provider.id}:probe", params={"project_id": str(project.id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "missing credentials" in data["message"].lower()


@pytest.mark.asyncio
async def test_probe_ollama_success(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    project = await crud.project.create(
        db=db_session,
        obj_in=schemas.ProjectCreate(name="Probe Ollama Test", owner="owner@example.com", tags=["llm"]),
    )

    provider = LLMProvider(
        kind=LLMProviderKind.OLLAMA, name="ollama-ok", base_url="http://localhost:11434", is_enabled=True
    )
    db_session.add(provider)
    await db_session.commit()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    resp = await async_client.post(
        f"/api/v1/admin/llm/providers/{provider.id}:probe", params={"project_id": str(project.id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "ollama ok" in data["message"].lower()
    assert "latency_ms=" in data["message"]

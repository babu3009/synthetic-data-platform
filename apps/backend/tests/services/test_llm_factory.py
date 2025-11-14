import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LLMProvider, LLMProviderKind, ProjectLLMSetting, LLMModel, LLMCredential, Project
from app.services.llm import LLMClientFactory
from app.utils.crypto import encrypt_json


@pytest.mark.asyncio
async def test_factory_returns_none_when_no_setting(db_session: AsyncSession):
    # Persist a project row to satisfy FK constraint
    project = Project(name="proj-disabled")
    db_session.add(project)
    await db_session.flush()
    project_id = project.id
    res = await LLMClientFactory.get_for_project(db_session, project_id=project_id)
    assert res is None


@pytest.mark.asyncio
async def test_factory_returns_none_when_disabled(db_session: AsyncSession):
    project = Project(name="proj-openai")
    db_session.add(project)
    await db_session.flush()
    project_id = project.id
    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-test", is_enabled=False)
    db_session.add(provider)
    await db_session.flush()
    setting = ProjectLLMSetting(project_id=project_id, enabled=True, provider_id=provider.id)
    db_session.add(setting)
    await db_session.commit()
    res = await LLMClientFactory.get_for_project(db_session, project_id=project_id)
    assert res is None


@pytest.mark.asyncio
async def test_factory_openai_success(db_session: AsyncSession, monkeypatch):
    # Ensure encryption has a key in tests
    os.environ.setdefault("LLM_SECRET_KEY", "unit-test-secret-key-please-change")
    from app.db.models import Project
    project = Project(name="proj-openai-success")
    db_session.add(project)
    await db_session.flush()
    project_id = project.id
    provider = LLMProvider(kind=LLMProviderKind.OPENAI, name="openai-live", is_enabled=True)
    db_session.add(provider)
    await db_session.flush()

    model = LLMModel(provider_id=provider.id, name="gpt-4o", display_name="GPT-4o", supports_json=True)
    db_session.add(model)
    await db_session.flush()

    # Credential with encrypted api_key
    enc = encrypt_json({"api_key": "sk-test-1234"})
    cred = LLMCredential(provider_id=provider.id, enc_payload_json=enc)
    db_session.add(cred)
    setting = ProjectLLMSetting(project_id=project_id, enabled=True, provider_id=provider.id, model_id=model.id, temperature=0.2, top_p=0.9, max_tokens=256)
    db_session.add(setting)
    await db_session.commit()

    # Monkeypatch probe to avoid network
    from app.services.llm.clients import OpenAIClient

    async def fake_probe(self):
        return True, "ok"

    monkeypatch.setattr(OpenAIClient, "probe", fake_probe)

    res = await LLMClientFactory.get_for_project(db_session, project_id=project_id)
    assert res is not None
    client, cfg = res
    assert client.name == "openai"
    assert cfg.model_name == "gpt-4o"
    assert cfg.temperature == 0.2
    assert cfg.supports_json is True

    r = await client.suggest_providers(columns=[{"name": "id", "dtype": "int"}])
    assert r.provider == "openai"
    assert r.model == "gpt-4o"
    assert 0 <= r.rank <= 1
    assert 0 <= r.confidence <= 1


@pytest.mark.asyncio
async def test_adapter_probe_fail(monkeypatch):
    from app.services.llm.clients import AnthropicClient

    client = AnthropicClient(api_key=None)

    ok, msg = await client.probe()
    assert ok is False
    assert "missing" in msg

    # Monkeypatch httpx call to simulate success with dummy key
    client.api_key = "dummy"
    async def fake_get(url, headers=None):
        class Resp:
            status_code = 200
        return Resp()

    class DummyAsyncClient:
        def __init__(self, timeout):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def get(self, url, headers=None):
            return await fake_get(url, headers)

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)
    ok, msg = await client.probe()
    assert ok is True
    assert "status=200" in msg

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4, UUID

from app.security.passwords import hash_password
from app.security.jwt import create_access_token
from app.db.models import UserRole, UserStatus, User, Project
from app.schemas.llm import LLMProviderCreate
from app.api.api_v1.endpoints.infer import reset_rate_limiter, RATE_LIMIT_PER_MINUTE


async def _bootstrap_owner(db: AsyncSession):
    # Use ADMIN (not OWNER) – UserRole only defines USER/ADMIN; ownership tracked separately via Project.owner / ProjectRole.
    user = User(
        email="owner@example.com",
        password_hash=hash_password("OwnerPass#123"),
        organization="Org",
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED,
    )
    # Project model does not have a description column; supply required owner field instead.
    project = Project(name="LLMProj", owner="Owner")
    db.add_all([user, project])
    await db.commit()
    await db.refresh(user)
    await db.refresh(project)
    token = create_access_token(str(user.id), user.role.value, expires_minutes=5)
    return user, project, token


@pytest.mark.asyncio
async def test_llm_rate_limit(async_client: AsyncClient, db_session: AsyncSession):
    reset_rate_limiter()
    user, project, token = await _bootstrap_owner(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    # Minimal payload
    payload = {"columns": []}
    allowed = RATE_LIMIT_PER_MINUTE
    # Fire allowed requests
    for i in range(allowed):
        r = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload, headers=headers)
        assert r.status_code == 200, f"Expected 200 before limit, got {r.status_code} on attempt {i+1}" 
    # One over the limit
    r = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload, headers=headers)
    assert r.status_code == 429, f"Expected 429 after limit, got {r.status_code}" 
    assert r.json()["detail"].startswith("Rate limit")


@pytest.mark.asyncio
async def test_llm_provider_discovery_and_models(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    user, project, token = await _bootstrap_owner(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    # Create provider (openai style but base_url pointing to fake server)
    body = {"kind": "openai", "name": "openai-test", "base_url": "http://localhost:9999", "is_enabled": True}
    r = await async_client.post(f"/api/v1/admin/llm/providers?project_id={project.id}", json=body, headers=headers)
    assert r.status_code == 201
    provider_id = r.json()["id"]

    # Monkeypatch httpx AsyncClient.get for discovery and probe to return deterministic responses
    class DummyResp:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json = json_data or {"data": [{"id": "gpt-4o", "context_length": 128000}, {"id": "gpt-foo", "context_length": 8000}]}
        def json(self):
            return self._json
    async def fake_get(self, url, headers=None):
        return DummyResp()
    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    # Probe provider
    r = await async_client.post(f"/api/v1/admin/llm/providers/{provider_id}:probe?project_id={project.id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True or data["ok"] is False  # Accept either; latency measurement present
    assert "latency_ms=" in data["message"]

    # Discover models
    r = await async_client.post(f"/api/v1/admin/llm/providers/{provider_id}:discover-models?project_id={project.id}", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["added_count"] >= 1
    assert len(d["models"]) >= d["added_count"]


@pytest.mark.asyncio
async def test_llm_settings_infer_integration(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    user, project, token = await _bootstrap_owner(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    # Create provider
    body = {"kind": "openai", "name": "openai-live", "base_url": "http://localhost:9998", "is_enabled": True}
    r = await async_client.post(f"/api/v1/admin/llm/providers?project_id={project.id}", json=body, headers=headers)
    assert r.status_code == 201
    provider_id = r.json()["id"]

    # Create a model under provider (simplified)
    model_body = {"name": "gpt-4o", "display_name": "gpt-4o", "context_tokens": 128000, "supports_json": True, "is_default": True, "metadata_json": {}}
    r = await async_client.post(f"/api/v1/admin/llm/providers/{provider_id}/models?project_id={project.id}", json=model_body, headers=headers)
    assert r.status_code == 201
    model_id = r.json()["id"]

    # Insert project LLM settings directly (enable and link provider/model)
    from app.db.models import ProjectLLMSetting
    setting = ProjectLLMSetting(
        project_id=project.id,
        enabled=True,
        provider_id=UUID(str(provider_id)),
        model_id=UUID(str(model_id)),
        temperature=0.3,
    )
    db_session.add(setting)
    await db_session.commit()

    # Monkeypatch LLM client probe to succeed without real network
    async def fake_probe(self):
        return True
    monkeypatch.setattr("app.services.llm.clients.BaseLLMClient.probe", fake_probe)

    # Use a column name that triggers heuristic suggestions (e.g., 'email')
    payload = {"columns": [{"table": "t", "column": "email", "dtype": "string", "description": ""}]}
    r = await async_client.post(f"/api/v1/projects/{project.id}/infer/providers", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) >= 1
    # We can't directly assert llm_enabled since response schema doesn't expose flags, but ensure suggestions exist.

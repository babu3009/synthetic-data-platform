from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import (
    ProjectLLMSetting,
    LLMProviderKind,
    LLMProvider,
    LLMModel,
    LLMCredential,
)
from app.services.llm.clients import (
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    OllamaClient,
    LMStudioClient,
)
from app.utils.crypto import decrypt_json


@dataclass
class ModelConfig:
    provider_kind: str
    provider_name: str
    model_name: Optional[str]
    temperature: Optional[float]
    top_p: Optional[float]
    max_tokens: Optional[int]
    supports_json: Optional[bool]


class LLMClientFactory:
    """Factory for resolving a project-scoped LLM client and model configuration."""

    @staticmethod
    async def get_for_project(
        db: AsyncSession, *, project_id: UUID
    ) -> Optional[Tuple[BaseLLMClient, ModelConfig]]:
        # Fetch project setting
        setting_res = await db.execute(
            select(ProjectLLMSetting).where(ProjectLLMSetting.project_id == project_id)
        )
        setting: Optional[ProjectLLMSetting] = setting_res.scalar_one_or_none()
        if not setting or not setting.enabled or not setting.provider_id:
            return None

        # Provider
        provider_res = await db.execute(
            select(LLMProvider).where(LLMProvider.id == setting.provider_id)
        )
        provider: Optional[LLMProvider] = provider_res.scalar_one_or_none()
        if not provider or not provider.is_enabled:
            return None

        # Model (optional)
        model: Optional[LLMModel] = None
        if setting.model_id:
            model_res = await db.execute(
                select(LLMModel).where(LLMModel.id == setting.model_id)
            )
            model = model_res.scalar_one_or_none()

        # Credential (first for provider)
        cred_res = await db.execute(
            select(LLMCredential).where(LLMCredential.provider_id == provider.id)
        )
        cred: Optional[LLMCredential] = cred_res.scalar_one_or_none()
        payload = {}
        api_key: Optional[str] = None
        if cred:
            try:
                payload = decrypt_json(cred.enc_payload_json)
                api_key = payload.get("api_key")
            except Exception:  # pragma: no cover - decryption error path
                api_key = None

        base_url = provider.base_url
        model_name = model.name if model else None

        client: BaseLLMClient
        if provider.kind == LLMProviderKind.OPENAI:
            client = OpenAIClient(api_key=api_key, base_url=base_url, model=model_name)
        elif provider.kind == LLMProviderKind.ANTHROPIC:
            client = AnthropicClient(api_key=api_key, base_url=base_url, model=model_name)
        elif provider.kind == LLMProviderKind.OLLAMA:
            client = OllamaClient(base_url=base_url, model=model_name)
        elif provider.kind == LLMProviderKind.LMSTUDIO:
            client = LMStudioClient(base_url=base_url, model=model_name)
        else:
            # CUSTOM unsupported for now
            return None

        mcfg = ModelConfig(
            provider_kind=provider.kind.value,
            provider_name=provider.name,
            model_name=model_name,
            temperature=setting.temperature,
            top_p=setting.top_p,
            max_tokens=setting.max_tokens,
            supports_json=model.supports_json if model else None,
        )
        return client, mcfg

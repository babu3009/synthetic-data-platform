"""Phase 5: Modular LLM client factory.

Relocated from `app/services/llm/factory.py` to live under the module
namespace. The legacy file now re-exports for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, cast
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
from app.modules.llm.clients import (
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
        setting_res = await db.execute(
            select(ProjectLLMSetting).where(ProjectLLMSetting.project_id == project_id)
        )
        setting: Optional[ProjectLLMSetting] = setting_res.scalar_one_or_none()
        if not setting:
            return None
        setting_enabled = cast(bool, setting.enabled)
        setting_provider_id = cast(Optional[UUID], setting.provider_id)
        if (not setting_enabled) or (not setting_provider_id):
            return None

        provider_res = await db.execute(
            select(LLMProvider).where(LLMProvider.id == setting.provider_id)
        )
        provider: Optional[LLMProvider] = provider_res.scalar_one_or_none()
        if not provider:
            return None
        provider_enabled = cast(bool, provider.is_enabled)
        if not provider_enabled:
            return None

        model: Optional[LLMModel] = None
        if cast(Optional[UUID], setting.model_id):
            model_res = await db.execute(
                select(LLMModel).where(LLMModel.id == setting.model_id)
            )
            model = model_res.scalar_one_or_none()

        cred_res = await db.execute(
            select(LLMCredential).where(LLMCredential.provider_id == provider.id)
        )
        cred: Optional[LLMCredential] = cred_res.scalar_one_or_none()
        payload = {}
        api_key: Optional[str] = None
        if cred:
            try:
                payload = decrypt_json(cast(str, cred.enc_payload_json))
                api_key = payload.get("api_key")
            except Exception:  # pragma: no cover
                api_key = None

        base_url = cast(Optional[str], provider.base_url)
        model_name = cast(Optional[str], model.name) if model else None

        pkind = cast(LLMProviderKind, provider.kind)
        if pkind == LLMProviderKind.OPENAI:
            client = OpenAIClient(api_key=api_key, base_url=base_url, model=model_name)
        elif pkind == LLMProviderKind.ANTHROPIC:
            client = AnthropicClient(api_key=api_key, base_url=base_url, model=model_name)
        elif pkind == LLMProviderKind.OLLAMA:
            client = OllamaClient(base_url=base_url, model=model_name)
        elif pkind == LLMProviderKind.LMSTUDIO:
            client = LMStudioClient(base_url=base_url, model=model_name)
        else:
            return None

        mcfg = ModelConfig(
            provider_kind=pkind.value,
            provider_name=cast(str, provider.name),
            model_name=model_name,
            temperature=cast(Optional[float], setting.temperature),
            top_p=cast(Optional[float], setting.top_p),
            max_tokens=cast(Optional[int], setting.max_tokens),
            supports_json=cast(Optional[bool], model.supports_json) if model else None,
        )
        return client, mcfg

__all__ = ["LLMClientFactory", "ModelConfig"]
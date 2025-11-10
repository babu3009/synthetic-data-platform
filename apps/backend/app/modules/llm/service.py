"""LLM service layer (Phase 2/5).

Provide thin wrappers around existing factory logic. Endpoints can be
migrated to call these functions without changing behavior.
"""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.llm.factory import LLMClientFactory, ModelConfig
from app.modules.llm.clients import BaseLLMClient


async def get_llm_for_project(db: AsyncSession, project_id: UUID) -> Optional[Tuple[BaseLLMClient, ModelConfig]]:
    """Resolve a project-scoped LLM client and model config, or None if disabled.

    Delegates to the existing factory to avoid behavior changes.
    """
    return await LLMClientFactory.get_for_project(db, project_id=project_id)


__all__ = ["get_llm_for_project"]

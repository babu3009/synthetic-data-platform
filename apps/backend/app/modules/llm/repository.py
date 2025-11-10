"""Thin DB accessors for LLM domain (Phase 2).

Keep queries centralized and import ORM models from app.db.models.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    ProjectLLMSetting,
    LLMProvider,
    LLMModel,
    LLMCredential,
)


async def get_setting_by_project(db: AsyncSession, project_id: UUID) -> Optional[ProjectLLMSetting]:
    res = await db.execute(select(ProjectLLMSetting).where(ProjectLLMSetting.project_id == project_id))
    return res.scalar_one_or_none()


async def get_provider(db: AsyncSession, provider_id: UUID) -> Optional[LLMProvider]:
    res = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    return res.scalar_one_or_none()


async def get_models_by_provider(db: AsyncSession, provider_id: UUID) -> List[LLMModel]:
    res = await db.execute(select(LLMModel).where(LLMModel.provider_id == provider_id))
    return list(res.scalars().all())


async def get_credential_by_provider(db: AsyncSession, provider_id: UUID) -> Optional[LLMCredential]:
    res = await db.execute(select(LLMCredential).where(LLMCredential.provider_id == provider_id))
    return res.scalar_one_or_none()

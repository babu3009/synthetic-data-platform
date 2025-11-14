from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import LLMProviderTaskDefault, LLMTaskType


class CRUDLLMProviderTaskDefault(CRUDBase[LLMProviderTaskDefault, LLMProviderTaskDefault, LLMProviderTaskDefault]):
    async def get_by_provider_and_task(
        self, db: AsyncSession, *, provider_id: UUID, task_type: LLMTaskType
    ) -> Optional[LLMProviderTaskDefault]:
        res = await db.execute(
            select(LLMProviderTaskDefault).where(
                LLMProviderTaskDefault.provider_id == provider_id,
                LLMProviderTaskDefault.task_type == task_type,
            )
        )
        return res.scalar_one_or_none()

    async def list_by_provider(self, db: AsyncSession, *, provider_id: UUID) -> list[LLMProviderTaskDefault]:
        res = await db.execute(
            select(LLMProviderTaskDefault).where(LLMProviderTaskDefault.provider_id == provider_id)
        )
        return list(res.scalars().all())


llm_task_default = CRUDLLMProviderTaskDefault(LLMProviderTaskDefault)

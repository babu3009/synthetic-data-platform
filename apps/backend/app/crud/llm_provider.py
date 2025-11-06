from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import LLMProvider
from app.schemas.llm import LLMProviderCreate, LLMProviderUpdate


class CRUDLLMProvider(CRUDBase[LLMProvider, LLMProviderCreate, LLMProviderUpdate]):
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[LLMProvider]:
        res = await db.execute(select(LLMProvider).where(LLMProvider.name == name))
        return res.scalar_one_or_none()

    async def list_enabled(self, db: AsyncSession) -> List[LLMProvider]:
        res = await db.execute(select(LLMProvider).where(LLMProvider.is_enabled == True))
        return res.scalars().all()


llm_provider = CRUDLLMProvider(LLMProvider)

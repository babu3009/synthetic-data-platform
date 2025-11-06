from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import LLMModel
from app.schemas.llm import LLMModelCreate


class CRUDLLMModel(CRUDBase[LLMModel, LLMModelCreate, LLMModelCreate]):
    async def get_by_provider(self, db: AsyncSession, *, provider_id: UUID) -> List[LLMModel]:
        res = await db.execute(select(LLMModel).where(LLMModel.provider_id == provider_id))
        return res.scalars().all()


llm_model = CRUDLLMModel(LLMModel)

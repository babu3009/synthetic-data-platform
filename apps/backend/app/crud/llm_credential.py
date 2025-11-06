from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import LLMCredential
from app.schemas.llm import LLMCredentialUpsert


class CRUDLLMCredential(CRUDBase[LLMCredential, LLMCredentialUpsert, LLMCredentialUpsert]):
    async def get_by_provider(self, db: AsyncSession, *, provider_id: UUID) -> Optional[LLMCredential]:
        res = await db.execute(select(LLMCredential).where(LLMCredential.provider_id == provider_id))
        return res.scalar_one_or_none()


llm_credential = CRUDLLMCredential(LLMCredential)

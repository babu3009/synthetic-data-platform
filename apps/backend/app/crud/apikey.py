"""API key CRUD and helpers."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import ApiKey
from app.schemas.apikey import ApiKeyCreate, ApiKeyUpdate


class CRUDApiKey(CRUDBase[ApiKey, ApiKeyCreate, ApiKeyUpdate]):
    async def get_by_hashed(self, db: AsyncSession, *, hashed_key: str) -> Optional[ApiKey]:
        res = await db.execute(select(ApiKey).where(ApiKey.hashed_key == hashed_key))
        return res.scalar_one_or_none()

    async def get_by_project(self, db: AsyncSession, *, project_id: UUID) -> List[ApiKey]:
        res = await db.execute(select(ApiKey).where(ApiKey.project_id == project_id))
        return list(res.scalars().all())


api_key = CRUDApiKey(ApiKey)

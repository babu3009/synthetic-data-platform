from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import ProjectLLMSetting
from app.schemas.llm import ProjectLLMSettingUpdate


class CRUDProjectLLMSetting(CRUDBase[ProjectLLMSetting, ProjectLLMSettingUpdate, ProjectLLMSettingUpdate]):
    async def get_by_project(self, db: AsyncSession, *, project_id: UUID) -> Optional[ProjectLLMSetting]:
        res = await db.execute(select(ProjectLLMSetting).where(ProjectLLMSetting.project_id == project_id))
        return res.scalar_one_or_none()


project_llm_setting = CRUDProjectLLMSetting(ProjectLLMSetting)

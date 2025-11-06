"""Project member CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import ProjectMember
from app.schemas.security import ProjectMemberCreate, ProjectMemberUpdate


class CRUDProjectMember(CRUDBase[ProjectMember, ProjectMemberCreate, ProjectMemberUpdate]):
    async def get_by_user(self, db: AsyncSession, *, project_id: UUID, user_sub: str) -> Optional[ProjectMember]:
        res = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_sub == user_sub,
            )
        )
        return res.scalar_one_or_none()

    async def list_for_project(self, db: AsyncSession, *, project_id: UUID) -> List[ProjectMember]:
        res = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
        return list(res.scalars().all())


project_member = CRUDProjectMember(ProjectMember)

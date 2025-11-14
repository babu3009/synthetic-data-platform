"""Project member CRUD."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import ProjectMember, User
from app.schemas.security import ProjectMemberCreate, ProjectMemberUpdate


class CRUDProjectMember(CRUDBase[ProjectMember, ProjectMemberCreate, ProjectMemberUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: ProjectMemberCreate) -> ProjectMember:
        data = obj_in.model_dump()
        user_id = data.get("user_id")
        user_sub = data.get("user_sub")
        if not user_id:
            if not user_sub:
                raise ValueError("user_id or user_sub is required")
            # Resolve by email/subject
            res = await db.execute(select(User).where(User.email == user_sub))
            u = res.scalar_one_or_none()
            if not u:
                # Create a placeholder user when not found (for tests/dev)
                from app.db.models import UserRole, UserStatus
                email = user_sub if "@" in user_sub else f"{user_sub}@local"
                u = User(email=email, password_hash="!", role=UserRole.USER, status=UserStatus.APPROVED)
                db.add(u)
                await db.commit()
                await db.refresh(u)
            user_id = u.id
        # Build model without legacy user_sub
        pm = ProjectMember(project_id=data["project_id"], user_id=user_id, role=data["role"])
        db.add(pm)
        await db.commit()
        await db.refresh(pm)
        return pm

    async def get_by_user(self, db: AsyncSession, *, project_id: UUID, user_id: UUID) -> Optional[ProjectMember]:
        res = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return res.scalar_one_or_none()

    async def list_for_project(self, db: AsyncSession, *, project_id: UUID) -> List[ProjectMember]:
        res = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
        return list(res.scalars().all())


project_member = CRUDProjectMember(ProjectMember)

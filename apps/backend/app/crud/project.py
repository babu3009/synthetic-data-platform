"""
Project CRUD operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """CRUD operations for Project model."""

    async def get_by_owner(
        self, db: AsyncSession, *, owner: str, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        """Get projects by owner."""
        result = await db.execute(
            select(Project)
            .where(Project.owner == owner)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_name_and_owner(
        self, db: AsyncSession, *, name: str, owner: str
    ) -> Optional[Project]:
        """Get project by name and owner."""
        result = await db.execute(
            select(Project)
            .where(Project.name == name)
            .where(Project.owner == owner)
        )
        return result.scalar_one_or_none()


project = CRUDProject(Project)
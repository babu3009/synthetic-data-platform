"""
Project CRUD operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import Project, User, UserRole, UserStatus
from sqlalchemy import select, func
from app.schemas.project import ProjectCreate, ProjectUpdate


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """CRUD operations for Project model."""

    async def create(self, db: AsyncSession, *, obj_in: ProjectCreate) -> Project:
        """Create a project, resolving legacy owner email to owner_user_id if provided.

        This keeps backward compatibility with tests or callers that still pass `owner`.
        """
        try:
            data = obj_in.model_dump(exclude_unset=True)  # pydantic v2
        except TypeError:
            data = obj_in.model_dump()  # test fakes may not accept kwargs
        owner_user_id: Optional[UUID] = data.get("owner_user_id")  # type: ignore
        owner_email: Optional[str] = data.get("owner")  # legacy

        if not owner_user_id and owner_email:
            res = await db.execute(select(User).where(func.lower(User.email) == func.lower(owner_email)))
            u = res.scalar_one_or_none()
            if not u:
                # Create placeholder user for tests/dev
                email = owner_email
                if "@" not in email:
                    email = f"{owner_email}@local"
                u = User(email=email, password_hash="!", role=UserRole.USER, status=UserStatus.APPROVED)
                db.add(u)
                await db.commit()
                await db.refresh(u)
            owner_user_id = u.id

        # Build without unsupported fields
        proj = Project(
            name=data["name"],
            owner_user_id=owner_user_id,
            tags=data.get("tags", []),
            webhook_run_status_url=data.get("webhook_run_status_url"),
            artifact_ttl_days=data.get("artifact_ttl_days"),
        )
        db.add(proj)
        await db.commit()
        await db.refresh(proj)
        return proj

    async def get_by_owner(
        self, db: AsyncSession, *, owner: str, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        """Get projects by legacy owner email. Joins users on owner_user_id."""
        result = await db.execute(
            select(Project)
            .join(User, Project.owner_user_id == User.id)
            .where(func.lower(User.email) == func.lower(owner))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_name_and_owner(
        self, db: AsyncSession, *, name: str, owner: str
    ) -> Optional[Project]:
        """Get project by name and legacy owner email using join."""
        result = await db.execute(
            select(Project)
            .join(User, Project.owner_user_id == User.id)
            .where(Project.name == name)
            .where(func.lower(User.email) == func.lower(owner))
        )
        return result.scalar_one_or_none()

    async def get_by_owner_user_id(
        self, db: AsyncSession, *, owner_user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        """Get projects by owner user id."""
        result = await db.execute(
            select(Project)
            .where(Project.owner_user_id == owner_user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_name_and_owner_user_id(
        self, db: AsyncSession, *, name: str, owner_user_id: UUID
    ) -> Optional[Project]:
        """Get project by name and owner user id (case-insensitive)."""
        result = await db.execute(
            select(Project)
            .where(func.lower(Project.name) == func.lower(name))
            .where(Project.owner_user_id == owner_user_id)
        )
        return result.scalar_one_or_none()


project = CRUDProject(Project)
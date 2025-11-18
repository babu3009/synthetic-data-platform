"""
Request CRUD operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import Request, RequestStatus
from app.schemas.request import RequestCreate, RequestUpdate
from app.utils.name_generator import generate_unique_alias


class CRUDRequest(CRUDBase[Request, RequestCreate, RequestUpdate]):
    """CRUD operations for Request model."""

    async def get_by_project(
        self, db: AsyncSession, *, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Request]:
        """Get requests by project ID."""
        result = await db.execute(
            select(Request)
            .where(Request.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_status(
        self, db: AsyncSession, *, status: RequestStatus, skip: int = 0, limit: int = 100
    ) -> List[Request]:
        """Get requests by status."""
        result = await db.execute(
            select(Request)
            .where(Request.status == status)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_with_project(
        self, db: AsyncSession, *, obj_in: RequestCreate, project_id: UUID
    ) -> Request:
        """Create request with project association."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["project_id"] = project_id
        
        # Generate alias if not provided
        if not obj_in_data.get("alias"):
            # Get existing aliases for this project to ensure uniqueness
            result = await db.execute(
                select(Request.alias)
                .where(Request.project_id == project_id)
                .where(Request.alias.isnot(None))
            )
            existing_aliases = set(row[0] for row in result.all())
            obj_in_data["alias"] = generate_unique_alias(existing_aliases)
        
        db_obj = Request(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


request = CRUDRequest(Request)
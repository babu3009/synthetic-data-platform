"""
Artifact CRUD operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.db.models import Artifact
from app.schemas.artifact import ArtifactCreate, ArtifactUpdate


class CRUDArtifact(CRUDBase[Artifact, ArtifactCreate, ArtifactUpdate]):
    """CRUD operations for Artifact model."""

    async def get_by_request(
        self, db: AsyncSession, *, request_id: UUID
    ) -> List[Artifact]:
        """Get artifacts by request ID."""
        result = await db.execute(
            select(Artifact).where(Artifact.request_id == request_id)
        )
        return result.scalars().all()

    async def create_with_request(
        self, db: AsyncSession, *, obj_in: ArtifactCreate, request_id: UUID
    ) -> Artifact:
        """Create artifact with request association."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["request_id"] = request_id
        db_obj = Artifact(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


artifact = CRUDArtifact(Artifact)
"""Storage module repository helpers (Phase 2).

Thin DB accessors for artifact-centric queries. These wrap existing CRUD
so that future storage-specific metadata tables can be added without
modifying endpoint logic.
"""

from __future__ import annotations

from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas


async def get_artifacts_for_request(db: AsyncSession, request_id: UUID) -> List[schemas.Artifact]:
    return await crud.artifact.get_by_request(db, request_id=request_id)


async def get_artifact(db: AsyncSession, artifact_id: UUID) -> schemas.Artifact | None:
    return await crud.artifact.get(db=db, id=artifact_id)


__all__ = [
    "get_artifacts_for_request",
    "get_artifact",
]

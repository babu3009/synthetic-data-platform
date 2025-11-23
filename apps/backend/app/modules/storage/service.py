"""Storage service layer (Phase 2).

Provides higher-level operations around artifact retrieval and signed
URL generation, delegating raw DB access to repository helpers and
leveraging existing storage abstraction (Minio/local).
"""

from __future__ import annotations

from typing import List, Dict, Any
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.services.storage import get_storage
from . import repository


async def list_artifacts(db: AsyncSession, *, request_id: UUID) -> List[schemas.Artifact]:
    req = await crud.request.get(db=db, id=request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return await repository.get_artifacts_for_request(db, request_id=request_id)


async def get_artifact(db: AsyncSession, *, request_id: UUID, artifact_id: UUID) -> schemas.Artifact:
    req = await crud.request.get(db=db, id=request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    artifact = await repository.get_artifact(db, artifact_id=artifact_id)
    if artifact is None or artifact.request_id != request_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


async def sign_artifact(db: AsyncSession, *, request_id: UUID, artifact_id: UUID, expires: int = 3600) -> Dict[str, Any]:
    art = await get_artifact(db, request_id=request_id, artifact_id=artifact_id)
    
    # Get request to fetch alias for filename prefix
    req = await crud.request.get(db=db, id=request_id)
    
    storage = get_storage()
    uri = str(getattr(art, "storage_uri", ""))
    object_name = uri
    if uri.startswith("s3://"):
        try:
            object_name = uri.split("/", 3)[3]
        except Exception:
            object_name = uri
    elif uri.startswith("file:") and "/requests/" in uri:
        object_name = uri.split("/requests/")[-1]
    
    # Build custom download filename with request alias prefix
    download_filename = None
    if req and req.alias:
        # Extract original filename from object_name
        original_filename = object_name.split("/")[-1]
        # Create prefixed filename: {alias}_{original_filename}
        download_filename = f"{req.alias}_{original_filename}"
    
    url = storage.get_signed_url(str(object_name), expires_seconds=int(expires), download_filename=download_filename)
    return {"url": url, "expires": int(expires)}


__all__ = [
    "list_artifacts",
    "get_artifact",
    "sign_artifact",
]

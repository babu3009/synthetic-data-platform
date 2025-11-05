from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.session import get_db


class RunStatusWebhookRegister(BaseModel):
    project_id: UUID = Field(..., description="Project ID")
    url: HttpUrl = Field(..., description="Callback URL for run-status updates")


router = APIRouter()


@router.post("/webhooks/run-status", response_model=schemas.Project)
async def register_run_status_webhook(
    *, db: AsyncSession = Depends(get_db), payload: RunStatusWebhookRegister
) -> schemas.Project:
    """Register or update a project's run-status webhook URL."""
    project = await crud.project.get(db=db, id=payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    updated = await crud.project.update(
        db=db,
        db_obj=project,
        obj_in={"webhook_run_status_url": str(payload.url)},
    )
    return updated

"""Project-level LLM settings endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import project_llm_setting as crud_setting
from app.db.session import get_db
from app.db.models import AuditEvent, ProjectRole, LLMModel
from sqlalchemy import select
from app.schemas.llm import ProjectLLMSettingOut, ProjectLLMSettingUpdate
from app.security.auth import get_current_principal, require_project_scope

router = APIRouter()


@router.get("/", response_model=ProjectLLMSettingOut)
async def get_settings(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    principal = Depends(get_current_principal),
):
    # Allow VIEWER/EDITOR/OWNER to read
    await require_project_scope(str(project_id), required_roles=[ProjectRole.VIEWER], principal=principal, db=db)
    s = await crud_setting.get_by_project(db, project_id=project_id)
    if s is None:
        # Return a default object (not persisted) for API ergonomics
        return ProjectLLMSettingOut(
            id=UUID(int=0),  # placeholder non-existent ID
            project_id=project_id,
            enabled=False,
            provider_id=None,
            model_id=None,
            temperature=None,
            top_p=None,
            max_tokens=None,
            guardrails_json={},
            updated_at=None,
        )
    return ProjectLLMSettingOut.model_validate(s)


@router.put("/", response_model=ProjectLLMSettingOut)
async def put_settings(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    body: ProjectLLMSettingUpdate,
    principal = Depends(get_current_principal),
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.EDITOR], principal=principal, db=db)
    existing = await crud_setting.get_by_project(db, project_id=project_id)

    # Server-side validation that model_id belongs to provider_id if both set
    if body.model_id and not body.provider_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="model_id requires provider_id")
    if body.model_id and body.provider_id:
        res = await db.execute(select(LLMModel).where(LLMModel.id == body.model_id))
        model = res.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if str(model.provider_id) != str(body.provider_id):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="model_id does not belong to provider_id")
    if existing:
        updated = await crud_setting.update(db, db_obj=existing, obj_in=body)
    else:
        # Create new
        data = body.model_dump()
        data["project_id"] = project_id
        db_obj = crud_setting.model(**data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        updated = db_obj

    actor = getattr(principal, "actor", "unknown")
    payload = body.model_dump()
    if payload.get("provider_id"):
        payload["provider_id"] = str(payload["provider_id"])
    if payload.get("model_id"):
        payload["model_id"] = str(payload["model_id"])
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.project_settings.update", payload_json=payload))
    await db.commit()

    return ProjectLLMSettingOut.model_validate(updated)

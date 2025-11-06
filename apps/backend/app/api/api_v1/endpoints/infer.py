from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.security.auth import get_current_principal, require_project_scope
from app.db.models import ProjectRole
from app import schemas
from app.services.providers_infer import ColumnSpec, infer_providers_combined
from app.services.llm import LLMClientFactory
from sqlalchemy.future import select
from app.db.models import ProjectLLMSetting
from uuid import UUID


router = APIRouter()
root_router = APIRouter()


@router.post("/providers", response_model=schemas.InferProvidersResponse)
async def infer_providers_for_project(
    *,
    project_id: str,
    payload: schemas.InferProvidersRequest,
    db: AsyncSession = Depends(get_db),
    principal = Depends(get_current_principal),
) -> schemas.InferProvidersResponse:
    # Require EDITOR or OWNER role or write:project scope
    await require_project_scope(
        project_id,
        required_scopes=["write:project"],
        required_roles=[ProjectRole.EDITOR, ProjectRole.OWNER],
        principal=principal,
        db=db,
    )
    cols = [ColumnSpec(table=c.table, column=c.column, dtype=c.dtype, description=c.description) for c in (payload.columns or [])]
    llm_enabled = False
    llm_provider = None
    temperature = None

    # Coerce project_id to UUID; if invalid, skip LLM usage but still return heuristic results
    try:
        pid_uuid = UUID(str(project_id))
    except Exception:
        pid_uuid = None

    if pid_uuid is not None:
        res = await db.execute(select(ProjectLLMSetting).where(ProjectLLMSetting.project_id == pid_uuid))
        setting = res.scalar_one_or_none()
        if setting and bool(getattr(setting, "enabled", False)) and getattr(setting, "provider_id", None):
            fac_res = await LLMClientFactory.get_for_project(db, project_id=pid_uuid)
            if fac_res:
                client, cfg = fac_res
                try:
                    await client.probe()
                except Exception:
                    pass
                llm_enabled = True
                llm_provider = cfg.provider_kind
                temperature = cfg.temperature

    combined = infer_providers_combined(
        cols,
        llm_enabled=llm_enabled,
        llm_provider=llm_provider,
        temperature=temperature,
    )
    items = [schemas.ColumnProviderSuggestions(**r) for r in combined]
    return schemas.InferProvidersResponse(results=items)


@root_router.post("/providers", response_model=schemas.InferProvidersResponse)
async def infer_providers_nonscoped(*, payload: schemas.InferProvidersRequest) -> schemas.InferProvidersResponse:
    # Non-scoped alias: optionally allow payload.llm to drive LLM path
    cols = [ColumnSpec(table=c.table, column=c.column, dtype=c.dtype, description=c.description) for c in (payload.columns or [])]
    llm_enabled = bool(payload.llm.enabled) if payload.llm else False
    llm_provider = (payload.llm.provider if payload.llm else None) or None
    temperature = payload.llm.temperature if payload.llm else None
    combined = infer_providers_combined(cols, llm_enabled=llm_enabled, llm_provider=llm_provider, temperature=temperature)
    items = [schemas.ColumnProviderSuggestions(**r) for r in combined]
    return schemas.InferProvidersResponse(results=items)

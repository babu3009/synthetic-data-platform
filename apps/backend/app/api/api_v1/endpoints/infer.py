from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.security.auth import get_current_principal, require_project_scope
from app.db.models import ProjectRole
from app import schemas
from app.services.providers_infer import ColumnSpec, LLMConfig, infer_providers


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
    try:
        cols = [ColumnSpec(table=c.table, column=c.column, dtype=c.dtype, description=c.description) for c in (payload.columns or [])]
        llm_cfg = None
        if payload.llm:
            llm_cfg = LLMConfig(
                enabled=bool(payload.llm.enabled),
                provider=(payload.llm.provider or None),
                model=(payload.llm.model or None),
                temperature=payload.llm.temperature,
            )
        raw = infer_providers(cols, llm=llm_cfg)
        # Coerce dicts into Suggestion models
        sug_models = [schemas.Suggestion(**s) for s in raw]
        return schemas.InferProvidersResponse(suggestions=sug_models)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@root_router.post("/providers", response_model=schemas.InferProvidersResponse)
async def infer_providers_nonscoped(*, payload: schemas.InferProvidersRequest) -> schemas.InferProvidersResponse:
    # Non-scoped alias: for cases where project context is not required. No RBAC here.
    cols = [ColumnSpec(table=c.table, column=c.column, dtype=c.dtype, description=c.description) for c in (payload.columns or [])]
    llm_cfg = None
    if payload.llm:
        llm_cfg = LLMConfig(
            enabled=bool(payload.llm.enabled),
            provider=(payload.llm.provider or None),
            model=(payload.llm.model or None),
            temperature=payload.llm.temperature,
        )
    raw = infer_providers(cols, llm=llm_cfg)
    sug_models = [schemas.Suggestion(**s) for s in raw]
    return schemas.InferProvidersResponse(suggestions=sug_models)

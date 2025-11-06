from __future__ import annotations

from typing import Any, Dict, Tuple
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.security.auth import get_current_principal, require_project_scope
from app.db.models import ProjectRole
from app import schemas
from app.services.providers_infer import ColumnSpec, infer_providers_combined
from app.services.llm import LLMClientFactory
from sqlalchemy.future import select
from app.db.models import ProjectLLMSetting, AuditEvent
from uuid import UUID
from app.core.config import settings


RATE_LIMIT_PER_MINUTE = settings.INFER_RATE_LIMIT_PER_MINUTE  # configurable per env


class _SimpleProjectRateLimiter:
    """Naive in-memory per-project per-minute rate limiter.

    Keyed by (project_id, minute_epoch) -> count. Not multi-process safe; sufficient for
    single-process deployment or can be replaced later with Redis.
    """

    def __init__(self):
        self._counts: Dict[Tuple[str, int], int] = {}

    def check(self, project_id: str) -> bool:
        now = int(time.time())
        window = now // 60
        key = (project_id, window)
        # Opportunistic cleanup of old windows every 100 calls
        if len(self._counts) > 1000:
            cutoff = window - 2
            self._counts = {k: v for k, v in self._counts.items() if k[1] >= cutoff}
        cnt = self._counts.get(key, 0) + 1
        self._counts[key] = cnt
        return cnt <= RATE_LIMIT_PER_MINUTE

    def reset(self):  # For tests
        self._counts.clear()


_project_infer_limiter = _SimpleProjectRateLimiter()


def reset_rate_limiter():  # convenience for tests
    _project_infer_limiter.reset()


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
    # Coerce project_id to UUID; if invalid, still enforce RL but audit without project linkage
    try:
        pid_uuid = UUID(str(project_id))
    except Exception:
        pid_uuid = None

    # Rate limit per project
    if not _project_infer_limiter.check(str(project_id)):
        # Emit audit event and return 429 (feature flag controlled)
        if settings.FF_ENABLE_RATE_LIMIT_AUDIT:
            actor = getattr(principal, "actor", "unknown")
            db.add(
                AuditEvent(
                    actor=actor,
                    project_id=pid_uuid,
                    action="llm.infer.rate_limited",
                    payload_json={"limit": RATE_LIMIT_PER_MINUTE},
                )
            )
            await db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded; try again later")

    cols = [ColumnSpec(table=c.table, column=c.column, dtype=c.dtype, description=c.description) for c in (payload.columns or [])]
    llm_enabled = False
    llm_provider = None
    temperature = None

    # pid_uuid already computed above

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

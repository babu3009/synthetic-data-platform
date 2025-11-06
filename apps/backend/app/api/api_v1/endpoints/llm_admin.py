"""Admin endpoints for managing LLM providers, credentials, and models.
OWNER role is required for all routes here.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import llm_provider as crud_provider, llm_model as crud_model, llm_credential as crud_cred
from app.db.session import get_db
from app.db.models import AuditEvent, ProjectRole
from app.schemas.llm import (
    LLMProvider,
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMCredentialCreate,
    LLMCredentialOut,
    LLMModelCreate,
    LLMModelOut,
    ProbeResponse,
    DiscoverModelsResponse,
)
from app.security.auth import get_current_principal, require_project_scope

router = APIRouter()


# Providers
@router.get("/providers", response_model=List[LLMProvider])
async def list_providers(
    *,
    db: AsyncSession = Depends(get_db),
    principal = Depends(get_current_principal),
    # Project scoping for admin: require OWNER of any project to access admin
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    providers = await crud_provider.get_multi(db)
    return [LLMProvider.model_validate(p) for p in providers]


@router.post("/providers", response_model=LLMProvider, status_code=status.HTTP_201_CREATED)
async def create_provider(
    *,
    db: AsyncSession = Depends(get_db),
    body: LLMProviderCreate,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    existing = await crud_provider.get_by_name(db, name=body.name)
    if existing:
        raise HTTPException(status_code=409, detail="Provider name already exists")
    created = await crud_provider.create(db, obj_in=body)

    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.provider.create", payload_json={
        "name": body.name, "kind": body.kind, "base_url": "<masked>" if body.base_url else None
    }))
    await db.commit()
    await db.refresh(created)
    return created


@router.patch("/providers/{provider_id}", response_model=LLMProvider)
async def update_provider(
    *,
    db: AsyncSession = Depends(get_db),
    provider_id: UUID,
    body: LLMProviderUpdate,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    updated = await crud_provider.update(db, db_obj=prov, obj_in=body)

    actor = getattr(principal, "actor", "unknown")
    payload = body.model_dump(exclude_unset=True)
    if "base_url" in payload:
        payload["base_url"] = "<masked>" if payload["base_url"] else None
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.provider.update", payload_json={"provider_id": str(provider_id), **payload}))
    await db.commit()
    await db.refresh(updated)
    return updated


# Credentials
@router.post("/providers/{provider_id}/credentials", response_model=LLMCredentialOut, status_code=status.HTTP_201_CREATED)
async def upsert_provider_credentials(
    *,
    db: AsyncSession = Depends(get_db),
    provider_id: UUID,
    body: LLMCredentialCreate,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")

    existing = await crud_cred.get_by_provider(db, provider_id=provider_id)
    if existing:
        # Update by replacing payload
        existing.enc_payload_json = body.enc_payload_json
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        cred = existing
    else:
        cred = await crud_cred.create(db, obj_in=body.__class__(enc_payload_json=body.enc_payload_json).model_copy(update={}))
        # Manually set provider if needed (CRUDBase doesn't pass foreign keys not in schema)
        cred.provider_id = provider_id
        db.add(cred)
        await db.commit()
        await db.refresh(cred)

    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.credential.upsert", payload_json={
        "provider_id": str(provider_id), "enc_payload_json": "<secret>"
    }))
    await db.commit()

    return LLMCredentialOut.model_validate(cred)


# Models
@router.get("/providers/{provider_id}/models", response_model=List[LLMModelOut])
async def list_models(
    *,
    db: AsyncSession = Depends(get_db),
    provider_id: UUID,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    models = await crud_model.get_by_provider(db, provider_id=provider_id)
    return [LLMModelOut.model_validate(m) for m in models]


@router.post("/providers/{provider_id}/models", response_model=LLMModelOut, status_code=status.HTTP_201_CREATED)
async def create_model(
    *,
    db: AsyncSession = Depends(get_db),
    provider_id: UUID,
    body: LLMModelCreate,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Create model under provider
    db_model = await crud_model.create(db, obj_in=body)
    db_model.provider_id = provider_id
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)

    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.model.create", payload_json={
        "provider_id": str(provider_id), "name": body.name, "display_name": body.display_name
    }))
    await db.commit()

    return LLMModelOut.model_validate(db_model)


# Operations
@router.post("/providers/{provider_id}:probe", response_model=ProbeResponse)
async def probe_provider(
    *,
    db: AsyncSession = Depends(get_db),
    provider_id: UUID,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    if not prov.is_enabled:
        return ProbeResponse(ok=False, message="Provider is disabled")
    # For now, we do a no-op probe. Future: attempt a trivial call using configured base_url/credentials.
    return ProbeResponse(ok=True, message="Probe succeeded (no-op)")


@router.post("/providers/{provider_id}:discover-models", response_model=DiscoverModelsResponse)
async def discover_models(
    *,
    db: AsyncSession = Depends(get_db),
    provider_id: UUID,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    # Placeholder: do not call external services during tests; return empty list.
    return DiscoverModelsResponse(models=[])

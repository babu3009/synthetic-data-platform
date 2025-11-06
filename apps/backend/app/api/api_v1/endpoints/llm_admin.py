"""Admin endpoints for managing LLM providers, credentials, and models.
OWNER role is required for all routes here.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.crud import llm_provider as crud_provider, llm_model as crud_model, llm_credential as crud_cred
from app.db.session import get_db
from app.db.models import AuditEvent, ProjectRole
from app.schemas.llm import (
    LLMProvider,
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMCredentialUpsert,
    LLMCredentialOut,
    LLMModelCreate,
    LLMModelOut,
    ProbeResponse,
    DiscoverModelsResponse,
)
from app.security.auth import get_current_principal, require_project_scope
from app.utils.crypto import encrypt_json, mask_secret

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
    body: LLMCredentialUpsert,
    principal = Depends(get_current_principal),
    project_id: UUID,
):
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    prov = await crud_provider.get(db, id=provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Build plaintext payload and encrypt
    payload = {
        "api_key": body.api_key,
        "org_id": body.org_id,
        "extra": body.extra or {},
    }
    cipher = encrypt_json(payload)

    existing = await crud_cred.get_by_provider(db, provider_id=provider_id)
    if existing:
        existing.enc_payload_json = cipher
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        cred = existing
    else:
        # Create new and set provider
        cred = await crud_cred.create(db, obj_in=type("Obj", (), {"model_dump": lambda self=None: {"enc_payload_json": cipher}})())
        cred.provider_id = provider_id
        db.add(cred)
        await db.commit()
        await db.refresh(cred)

    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.credential.upsert", payload_json={
        "provider_id": str(provider_id), "api_key": "***" + (body.api_key[-4:] if body.api_key else "")
    }))
    await db.commit()

    out = LLMCredentialOut.model_validate(cred)
    out.masked_api_key = mask_secret(body.api_key)
    return out


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

    # Helper: fetch credentials (for providers that need API keys)
    api_key: Optional[str] = None
    cred = await crud_cred.get_by_provider(db, provider_id=provider_id)
    if cred is not None:
        try:
            from app.utils.crypto import decrypt_json
            payload = decrypt_json(cred.enc_payload_json)
            api_key = (payload or {}).get("api_key")
        except Exception:
            api_key = None

    base_url = (prov.base_url or "").rstrip("/")

    discovered: List[Dict[str, Any]] = []

    async def _openai_discover() -> List[Dict[str, Any]]:
        url = (base_url or "https://api.openai.com/v1") + "/models"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("data", []) if isinstance(data, dict) else []
            out = []
            for it in items:
                model_id = it.get("id") or it.get("name")
                if not model_id:
                    continue
                # Heuristic: chat-capable models
                id_lower = str(model_id).lower()
                is_chat = any(k in id_lower for k in ["gpt", "turbo", "chat", "o1", "o3", "4o"])  # heuristic
                if not is_chat:
                    continue
                supports_json = ("json" in id_lower) or ("4o" in id_lower) or ("4.1" in id_lower)
                context_tokens = (
                    it.get("context_length")
                    or it.get("context_window")
                    or it.get("input_context_length")
                )
                out.append({
                    "name": model_id,
                    "display_name": model_id,
                    "context_tokens": context_tokens,
                    "supports_json": bool(supports_json),
                    "metadata_json": it if isinstance(it, dict) else {},
                })
            return out
        except Exception:
            return []

    async def _anthropic_discover() -> List[Dict[str, Any]]:
        url = (base_url or "https://api.anthropic.com") + "/v1/models"
        headers = {"x-api-key": api_key or "", "anthropic-version": "2023-06-01"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            # Some responses use {"data": [...]}, keep flexible
            items = []
            if isinstance(data, dict):
                if isinstance(data.get("data"), list):
                    items = data.get("data", [])
                elif isinstance(data.get("models"), list):
                    items = data.get("models", [])
            out = []
            for it in items:
                model_id = it.get("id") or it.get("name")
                if not model_id:
                    continue
                context_tokens = (
                    it.get("context_length")
                    or it.get("input_token_limit")
                    or it.get("input_tokens")
                )
                out.append({
                    "name": model_id,
                    "display_name": it.get("display_name") or model_id,
                    "context_tokens": context_tokens,
                    "supports_json": False,  # default unknown
                    "metadata_json": it if isinstance(it, dict) else {},
                })
            return out
        except Exception:
            return []

    async def _ollama_discover() -> List[Dict[str, Any]]:
        url = (base_url or "http://localhost:11434") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("models", []) if isinstance(data, dict) else []
            out = []
            for it in items:
                # Prefer the full tagged name like "llama3:instruct"
                model_name = it.get("model") or it.get("name")
                if not model_name:
                    continue
                out.append({
                    "name": model_name,
                    "display_name": it.get("name") or model_name,
                    "context_tokens": None,
                    "supports_json": False,
                    "metadata_json": it if isinstance(it, dict) else {},
                })
            return out
        except Exception:
            return []

    async def _lmstudio_discover() -> List[Dict[str, Any]]:
        url = (base_url or "http://localhost:1234") + "/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("data", []) if isinstance(data, dict) else []
            out = []
            for it in items:
                model_id = it.get("id") or it.get("name")
                if not model_id:
                    continue
                out.append({
                    "name": model_id,
                    "display_name": model_id,
                    "context_tokens": None,
                    "supports_json": False,
                    "metadata_json": it if isinstance(it, dict) else {},
                })
            return out
        except Exception:
            return []

    # Discover per provider kind
    if str(prov.kind.value) == "openai":
        discovered = await _openai_discover()
    elif str(prov.kind.value) == "anthropic":
        discovered = await _anthropic_discover()
    elif str(prov.kind.value) == "ollama":
        discovered = await _ollama_discover()
    elif str(prov.kind.value) == "lmstudio":
        discovered = await _lmstudio_discover()
    else:
        discovered = []

    # Upsert into DB (no duplicates by provider+name)
    existing_models = await crud_model.get_by_provider(db, provider_id=provider_id)
    existing_by_name = {m.name: m for m in existing_models}

    added = 0
    updated = 0
    unchanged = 0

    # Determine default: if none exists, we'll mark the first discovered as default
    has_default = any(getattr(m, "is_default", False) for m in existing_models)
    default_assigned_id: Optional[UUID] = None

    # Create or update
    for item in discovered:
        name = item.get("name")
        if not name:
            continue
        display_name = item.get("display_name") or name
        context_tokens = item.get("context_tokens")
        supports_json = bool(item.get("supports_json") or False)
        metadata_json = item.get("metadata_json") or {}

        if name in existing_by_name:
            m = existing_by_name[name]
            # Check diffs
            changed = False
            if m.display_name != display_name:
                m.display_name = display_name
                changed = True
            if m.context_tokens != context_tokens:
                m.context_tokens = context_tokens
                changed = True
            if bool(m.supports_json) != supports_json:
                m.supports_json = supports_json
                changed = True
            if (m.metadata_json or {}) != (metadata_json or {}):
                m.metadata_json = metadata_json
                changed = True
            if changed:
                db.add(m)
                await db.commit()
                await db.refresh(m)
                updated += 1
            else:
                unchanged += 1
        else:
            db_model = await crud_model.create(db, obj_in=LLMModelCreate(
                name=name,
                display_name=display_name,
                context_tokens=context_tokens,
                supports_json=supports_json,
                is_default=False,
                metadata_json=metadata_json,
            ))
            # Attach to provider
            db_model.provider_id = provider_id
            db.add(db_model)
            await db.commit()
            await db.refresh(db_model)
            added += 1
            existing_by_name[name] = db_model

    # If no default exists, set the first discovered (if any) as default
    if not has_default and discovered:
        # pick the first one that also exists in DB now
        first_name = discovered[0].get("name")
        if first_name and first_name in existing_by_name:
            target = existing_by_name[first_name]
            # unset others
            for m in existing_by_name.values():
                if m.is_default and m.id != target.id:
                    m.is_default = False
                    db.add(m)
            target.is_default = True
            db.add(target)
            await db.commit()
            default_assigned_id = target.id

    # Final list
    models = await crud_model.get_by_provider(db, provider_id=provider_id)

    # Audit
    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="llm.model.discover", payload_json={
        "provider_id": str(provider_id),
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "default_assigned_id": str(default_assigned_id) if default_assigned_id else None,
    }))
    await db.commit()

    return DiscoverModelsResponse(
        models=[LLMModelOut.model_validate(m) for m in models],
        added_count=added,
        updated_count=updated,
        unchanged_count=unchanged,
    )

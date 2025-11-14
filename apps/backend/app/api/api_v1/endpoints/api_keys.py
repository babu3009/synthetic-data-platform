"""API key management endpoints."""
from typing import List, Optional
from uuid import UUID
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import crud
from app.db.session import get_db
from app.schemas.apikey import ApiKeyCreate, ApiKeyOut
from app.security.auth import require_project_scope, sha256_key, get_current_principal
from app.db.models import ProjectRole, AuditEvent, ApiKey as ApiKeyModel

router = APIRouter()


@router.get("/", response_model=List[ApiKeyOut])
async def list_api_keys(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    principal = Depends(get_current_principal),
):
    """List API keys for a project with optional pagination and name search.

    - Authorization: OWNER only
    - Query params:
      - skip: offset for pagination
      - limit: max rows (capped to 200)
      - q: case-insensitive substring on `name`
    """
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    limit_capped = max(1, min(limit, 200))
    stmt = select(ApiKeyModel).where(ApiKeyModel.project_id == project_id)
    if q:
        # Use ILIKE for case-insensitive match when supported; fallback behavior acceptable
        try:
            from sqlalchemy import func
            stmt = stmt.where(ApiKeyModel.name.ilike(f"%{q}%"))  # type: ignore[attr-defined]
        except Exception:
            stmt = stmt.where(func.lower(ApiKeyModel.name).contains(q.lower()))  # type: ignore
    stmt = stmt.order_by(ApiKeyModel.created_at.desc()).offset(skip).limit(limit_capped)
    res = await db.execute(stmt)
    keys = list(res.scalars().all())
    return [ApiKeyOut.model_validate(k) for k in keys]


@router.post("/", response_model=ApiKeyOut, status_code=201)
async def create_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    body: ApiKeyCreate,
    principal = Depends(get_current_principal),
):
    # Only OWNER can create keys
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)

    # Generate secret and hash
    plaintext = secrets.token_urlsafe(32)
    hashed = sha256_key(plaintext)

    # Persist
    db_obj = await crud.api_key.create(db, obj_in=type("Obj", (), {
        "model_dump": lambda self=None: {
            "project_id": project_id,
            "name": body.name,
            "hashed_key": hashed,
            "scopes": body.scopes,
        }
    })())

    # Audit
    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="api_key.create", payload_json={"name": body.name, "scopes": body.scopes}))
    await db.commit()

    out = ApiKeyOut.model_validate(db_obj)
    out.plaintext_key = plaintext
    return out


@router.delete("/{key_id}", response_model=ApiKeyOut)
async def revoke_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    key_id: UUID,
    principal = Depends(get_current_principal),
):
    # Only OWNER can revoke keys
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    key = await crud.api_key.get(db, id=key_id)
    if not key or str(key.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Key not found")
    await crud.api_key.remove(db, id=key_id)

    actor = getattr(principal, "actor", "unknown")
    db.add(AuditEvent(actor=actor, project_id=project_id, action="api_key.revoke", payload_json={"key_id": str(key_id)}))
    await db.commit()

    return key


@router.get("/scopes", response_model=List[str])
async def list_api_key_scopes(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    principal = Depends(get_current_principal),
):
    """Enumerate available API key scopes for clients to present.

    Owner-only endpoint for now to keep shape simple.
    Mirrors documented scopes in SECURITY.md.
    """
    await require_project_scope(str(project_id), required_roles=[ProjectRole.OWNER], principal=principal, db=db)
    return [
        "read:project",
        "write:project",
        "run:request",
        "read:artifacts",
    ]

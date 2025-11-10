"""Admin service layer (Phase 2).

Implements user moderation operations using the repository and emits
audit events. Public functions mirror legacy endpoint behavior.
"""
from __future__ import annotations

from typing import Sequence, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserStatus
from app.services.audit import audit
from . import repository
from . import schemas as admin_schemas


async def list_users(db: AsyncSession, *, status: str = "PENDING_ADMIN_APPROVAL") -> admin_schemas.AdminUserListResponse:
    try:
        status_enum = getattr(UserStatus, status)
    except AttributeError:
        status_enum = UserStatus.PENDING_ADMIN_APPROVAL
    users = await repository.list_users_by_status(db, status_enum)
    return admin_schemas.AdminUserListResponse(
        users=[
            admin_schemas.AdminUser(
                id=str(u.id), email=str(u.email), organization=getattr(u, "organization", None), status=u.status.value
            )
            for u in users
        ]
    )


async def approve_user(db: AsyncSession, *, admin_id: str, user_id: str) -> Dict[str, Any]:
    await repository.set_user_status(db, user_id, UserStatus.APPROVED)
    await audit(db, "admin.user.approve", actor_user_id=admin_id, payload={"user_id": user_id})
    return {"status": "ok"}


async def reject_user(db: AsyncSession, *, admin_id: str, user_id: str) -> Dict[str, Any]:
    await repository.set_user_status(db, user_id, UserStatus.REJECTED)
    await audit(db, "admin.user.reject", actor_user_id=admin_id, payload={"user_id": user_id})
    return {"status": "ok"}


__all__ = ["list_users", "approve_user", "reject_user"]

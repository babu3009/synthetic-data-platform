"""Admin repository helpers (Phase 2).

Thin DB access layer for admin-related operations.
"""
from __future__ import annotations

from typing import Sequence, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models import User, UserStatus


async def list_users_by_status(db: AsyncSession, status: UserStatus) -> Sequence[User]:
    res = await db.execute(select(User).where(User.status == status))
    return tuple(res.scalars().all())


async def set_user_status(db: AsyncSession, user_id: Union[str, UUID], status: UserStatus) -> None:
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    await db.execute(update(User).where(User.id == user_id).values(status=status))
    await db.commit()


__all__ = ["list_users_by_status", "set_user_status"]

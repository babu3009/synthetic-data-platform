"""Auth repository abstractions (Phase 2).

Thin wrappers around existing CRUD modules to provide a stable module-local
import path while we refactor internals incrementally.
"""

from typing import Optional, Union
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User, EmailOTP, UserStatus, EmailOTPPurpose
from app.crud import users as users_crud
from app.crud import otps as otps_crud
from uuid import UUID


# Users
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
	return await users_crud.get_by_email(db, email)


async def get_user_by_id(db: AsyncSession, user_id: Union[str, UUID]) -> Optional[User]:
	# Coerce to UUID for SQLAlchemy UUID(as_uuid=True) columns
	if isinstance(user_id, str):
		try:
			user_id = UUID(user_id)
		except Exception:
			# Leave as-is; comparison may fail fast upstream if invalid
			pass
	res = await db.execute(select(User).where(User.id == user_id))
	return res.scalar_one_or_none()


async def create_user(db: AsyncSession, *, email: str, password_hash: str, organization: Optional[str]) -> User:
	return await users_crud.create_user(db, email=email, password_hash=password_hash, organization=organization)


async def set_user_status(db: AsyncSession, user_id: Union[str, UUID], status: UserStatus) -> None:
	await users_crud.set_status(db, user_id, status)


async def update_user_password(db: AsyncSession, user_id: Union[str, UUID], password_hash: str) -> None:
	await users_crud.update_password(db, user_id, password_hash)


async def set_last_login(db: AsyncSession, user_id: Union[str, UUID]) -> None:
	await users_crud.set_last_login(db, user_id)


# OTPs
async def create_otp(db: AsyncSession, *, user_id: Union[str, UUID], purpose: EmailOTPPurpose, otp_hash: str, expires_at: datetime) -> EmailOTP:
	return await otps_crud.create_otp(db, user_id, purpose, otp_hash, expires_at)


async def get_active_otp(db: AsyncSession, user_id: Union[str, UUID], purpose: EmailOTPPurpose) -> Optional[EmailOTP]:
	return await otps_crud.get_active_otp(db, user_id, purpose)


async def mark_otp_used(db: AsyncSession, otp_id: Union[str, UUID]) -> None:
	await otps_crud.mark_used(db, otp_id)


async def increment_otp_attempts(db: AsyncSession, otp_id: Union[str, UUID]) -> None:
	await otps_crud.increment_attempts(db, otp_id)


async def count_recent_otps(db: AsyncSession, user_id: Union[str, UUID], purpose: EmailOTPPurpose, since: datetime) -> int:
	return await otps_crud.count_recent_otps(db, user_id, purpose, since)


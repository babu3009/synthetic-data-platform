from typing import Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models import User


async def get_user_by_id(db: AsyncSession, user_id: Union[str, UUID]) -> Optional[User]:
	if isinstance(user_id, str):
		try:
			user_id = UUID(user_id)
		except Exception:
			# If not a valid UUID, no match will be found anyway
			return None
	res = await db.execute(select(User).where(User.id == user_id))
	return res.scalar_one_or_none()


async def set_user_avatar_url(db: AsyncSession, user_id: Union[str, UUID], url: str) -> None:
	if isinstance(user_id, str):
		user_id = UUID(user_id)
	await db.execute(update(User).where(User.id == user_id).values(profile_image_url=url))
	await db.commit()

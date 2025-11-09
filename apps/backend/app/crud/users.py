from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models import User, UserStatus

async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.email == email.lower()))
    return res.scalar_one_or_none()

async def create_user(db: AsyncSession, email: str, password_hash: str, organization: Optional[str]) -> User:
    user = User(email=email.lower(), password_hash=password_hash, organization=organization)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def set_status(db: AsyncSession, user_id: str, status: UserStatus) -> None:
    await db.execute(update(User).where(User.id == user_id).values(status=status))
    await db.commit()

async def update_password(db: AsyncSession, user_id: str, password_hash: str) -> None:
    await db.execute(update(User).where(User.id == user_id).values(password_hash=password_hash))
    await db.commit()

async def set_last_login(db: AsyncSession, user_id: str) -> None:
    from sqlalchemy import func
    await db.execute(update(User).where(User.id == user_id).values(last_login_at=func.now()))
    await db.commit()

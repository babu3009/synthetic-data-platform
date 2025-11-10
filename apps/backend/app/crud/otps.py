from typing import Optional, Union
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models import EmailOTP, EmailOTPPurpose
from uuid import UUID

async def create_otp(db: AsyncSession, user_id: Union[str, UUID], purpose: EmailOTPPurpose, otp_hash: str, expires_at: datetime) -> EmailOTP:
    # Normalize to UUID instance to satisfy SQLAlchemy UUID(as_uuid=True) columns which
    # expect .hex access on bound values when compiling for some dialects.
    if isinstance(user_id, str):
        try:
            user_id = UUID(user_id)
        except Exception:
            # Let DB layer raise if invalid, but avoid attribute errors here
            pass
    otp = EmailOTP(user_id=user_id, purpose=purpose, otp_hash=otp_hash, expires_at=expires_at)
    db.add(otp)
    await db.commit()
    await db.refresh(otp)
    return otp

async def get_active_otp(db: AsyncSession, user_id: Union[str, UUID], purpose: EmailOTPPurpose) -> Optional[EmailOTP]:
    if isinstance(user_id, str):
        try:
            user_id = UUID(user_id)
        except Exception:
            pass
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(EmailOTP)
        .where(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.used_at.is_(None),
            EmailOTP.expires_at > now,
        )
        .order_by(EmailOTP.created_at.desc())
        .limit(1)
    )
    # Using scalars().first() avoids MultipleResultsFound and returns None if empty
    return res.scalars().first()

async def mark_used(db: AsyncSession, otp_id: Union[str, UUID]) -> None:
    if isinstance(otp_id, str):
        try:
            otp_id = UUID(otp_id)
        except Exception:
            pass
    from sqlalchemy import func
    await db.execute(update(EmailOTP).where(EmailOTP.id == otp_id).values(used_at=func.now()))
    await db.commit()

async def increment_attempts(db: AsyncSession, otp_id: Union[str, UUID]) -> None:
    if isinstance(otp_id, str):
        try:
            otp_id = UUID(otp_id)
        except Exception:
            pass
    await db.execute(update(EmailOTP).where(EmailOTP.id == otp_id).values(attempts=EmailOTP.attempts + 1))
    await db.commit()

async def count_recent_otps(db: AsyncSession, user_id: Union[str, UUID], purpose: EmailOTPPurpose, since: datetime) -> int:
    if isinstance(user_id, str):
        try:
            user_id = UUID(user_id)
        except Exception:
            pass
    res = await db.execute(
        select(func.count(EmailOTP.id)).where(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.created_at >= since,
        )
    )
    return int(res.scalar() or 0)

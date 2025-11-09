from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models import EmailOTP, EmailOTPPurpose

async def create_otp(db: AsyncSession, user_id: str, purpose: EmailOTPPurpose, otp_hash: str, expires_at: datetime) -> EmailOTP:
    otp = EmailOTP(user_id=user_id, purpose=purpose, otp_hash=otp_hash, expires_at=expires_at)
    db.add(otp)
    await db.commit()
    await db.refresh(otp)
    return otp

async def get_active_otp(db: AsyncSession, user_id: str, purpose: EmailOTPPurpose) -> Optional[EmailOTP]:
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(EmailOTP).where(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.used_at.is_(None),
            EmailOTP.expires_at > now,
        ).order_by(EmailOTP.created_at.desc())
    )
    return res.scalar_one_or_none()

async def mark_used(db: AsyncSession, otp_id: str) -> None:
    from sqlalchemy import func
    await db.execute(update(EmailOTP).where(EmailOTP.id == otp_id).values(used_at=func.now()))
    await db.commit()

async def increment_attempts(db: AsyncSession, otp_id: str) -> None:
    await db.execute(
        update(EmailOTP).where(EmailOTP.id == otp_id).values(attempts=EmailOTP.attempts + 1)
    )
    await db.commit()

async def count_recent_otps(db: AsyncSession, user_id: str, purpose: EmailOTPPurpose, since: datetime) -> int:
    res = await db.execute(
        select(func.count(EmailOTP.id)).where(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == purpose,
            EmailOTP.created_at >= since,
        )
    )
    return int(res.scalar() or 0)

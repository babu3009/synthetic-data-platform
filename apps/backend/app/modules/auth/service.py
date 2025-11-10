"""Auth service layer (Phase 2).

Provides higher-level orchestration functions that wrap existing endpoint logic
and CRUD operations. Endpoints can gradually migrate to call these helpers,
improving testability and separation of concerns.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import UserStatus, EmailOTPPurpose
from app.security.passwords import hash_password, verify_password, validate_password_policy
from app.security.jwt import create_access_token
from app.services.otp import generate_otp_and_hash, verify_otp
from app.services.mailer import send_email, render_otp_email
from app.services.audit import audit
from . import repository


async def register_user(db: AsyncSession, email: str, password: str, organization: Optional[str]) -> Tuple[str, str]:
	"""Create user and issue verification OTP. Returns (user_id, status)."""
	validate_password_policy(password)
	existing = await repository.get_user_by_email(db, email)
	if existing:
		return str(existing.id), "exists"
	pwd_hash = hash_password(password)
	user = await repository.create_user(db, email=email, password_hash=pwd_hash, organization=organization)
	otp, otp_hash, expires_at = generate_otp_and_hash(str(user.id), EmailOTPPurpose.EMAIL_VERIFY.value, settings.EMAIL_OTP_TTL_HOURS)
	await repository.create_otp(db, user_id=str(user.id), purpose=EmailOTPPurpose.EMAIL_VERIFY, otp_hash=otp_hash, expires_at=expires_at)
	subject, html = render_otp_email(otp, "email_verify")
	send_email(str(user.email), subject, html)  # could be background task in endpoint
	await audit(db, "register.requested", actor_user_id=str(user.id), payload={"email": str(user.email)})
	return str(user.id), "created"


async def verify_email(db: AsyncSession, user_id: str, otp: str) -> str:
	otp_rec = await repository.get_active_otp(db, user_id, EmailOTPPurpose.EMAIL_VERIFY)
	if not otp_rec:
		raise ValueError("No active OTP")
	# attempts may be a SQLAlchemy Column value; cast safely
	attempts_val = int(getattr(otp_rec, "attempts", 0) or 0)
	if attempts_val >= settings.OTP_MAX_ATTEMPTS:
		raise ValueError("Too many attempts")
	if not verify_otp(user_id, EmailOTPPurpose.EMAIL_VERIFY.value, otp, str(otp_rec.otp_hash)):
		await repository.increment_otp_attempts(db, str(otp_rec.id))
		raise ValueError("Invalid code")
	await repository.mark_otp_used(db, str(otp_rec.id))
	# auto approve by domain (duplicated minimally; centralize later)
	domain_allow = {d.strip().lower() for d in settings.ALLOWED_AUTO_APPROVE_DOMAINS.split(',') if d.strip()}
	email = await _email_for_user(db, user_id)
	domain = email.split("@")[-1].lower() if email else ""
	new_status = UserStatus.APPROVED if domain in domain_allow else UserStatus.PENDING_ADMIN_APPROVAL
	await repository.set_user_status(db, user_id, new_status)
	await audit(db, "verify_email.success", actor_user_id=user_id, payload={"status": new_status.value})
	return new_status.value


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Tuple[str, str, str]:
	user = await repository.get_user_by_email(db, email)
	if not user:
		raise ValueError("Invalid credentials")
	if str(user.status.value) != UserStatus.APPROVED.value:  # type: ignore
		raise ValueError("User not approved")
	if not verify_password(password, str(user.password_hash)):
		raise ValueError("Invalid credentials")
	token = create_access_token(str(user.id), str(user.role), expires_minutes=60)
	await repository.set_last_login(db, str(user.id))
	return token, str(user.role), str(user.id)


async def issue_resend_email_otp(db: AsyncSession, user_id: str) -> str:
	"""Create a new EMAIL_VERIFY OTP if within resend limits and return the plain OTP.

	Rate limit semantics: allow up to OTP_RESEND_RATE_PER_HOUR resends in addition to the
	initial registration OTP within the rolling 1 hour window.
	"""
	since = datetime.now(timezone.utc) - timedelta(hours=1)
	max_req = max(1, settings.OTP_RESEND_RATE_PER_HOUR)
	recent = await repository.count_recent_otps(db, user_id, EmailOTPPurpose.EMAIL_VERIFY, since)
	# Exclude the initial registration OTP from resend accounting if present
	effective_recent = max(0, int(recent) - 1)
	if effective_recent >= max_req:
		raise ValueError("Too many resend attempts")
	otp, otp_hash, expires_at = generate_otp_and_hash(user_id, EmailOTPPurpose.EMAIL_VERIFY.value, settings.EMAIL_OTP_TTL_HOURS)
	await repository.create_otp(db, user_id=user_id, purpose=EmailOTPPurpose.EMAIL_VERIFY, otp_hash=otp_hash, expires_at=expires_at)
	return otp


async def _email_for_user(db: AsyncSession, user_id: str) -> Optional[str]:
	from sqlalchemy import select
	from app.db.models import User
	res = await db.execute(select(User.email).where(User.id == user_id))
	return res.scalar_one_or_none()


async def request_change_password_otp(db: AsyncSession, user_id: str) -> str:
	since = datetime.now(timezone.utc) - timedelta(hours=1)
	max_req = max(1, settings.OTP_RESEND_RATE_PER_HOUR)
	recent = await repository.count_recent_otps(db, user_id, EmailOTPPurpose.CHANGE_PWD, since)
	if recent >= max_req:
		raise ValueError("Too many requests")
	otp, otp_hash, expires_at = generate_otp_and_hash(user_id, EmailOTPPurpose.CHANGE_PWD.value, settings.EMAIL_OTP_TTL_HOURS)
	await repository.create_otp(db, user_id=user_id, purpose=EmailOTPPurpose.CHANGE_PWD, otp_hash=otp_hash, expires_at=expires_at)
	return otp


async def issue_forgot_password_otp(db: AsyncSession, user_id: str) -> str:
	since = datetime.now(timezone.utc) - timedelta(hours=1)
	max_req = max(1, settings.OTP_RESEND_RATE_PER_HOUR)
	recent = await repository.count_recent_otps(db, user_id, EmailOTPPurpose.FORGOT_PWD, since)
	if recent >= max_req:
		raise ValueError("Too many requests")
	otp, otp_hash, expires_at = generate_otp_and_hash(user_id, EmailOTPPurpose.FORGOT_PWD.value, settings.FORGOT_PWD_OTP_TTL_HOURS)
	await repository.create_otp(db, user_id=user_id, purpose=EmailOTPPurpose.FORGOT_PWD, otp_hash=otp_hash, expires_at=expires_at)
	return otp  # Caller sends email


async def reset_password_with_otp(db: AsyncSession, user_id: str, otp: str, new_password: str) -> None:
	otp_rec = await repository.get_active_otp(db, user_id, EmailOTPPurpose.FORGOT_PWD)
	if not otp_rec:
		raise ValueError("No active OTP")
	attempts_val = int(getattr(otp_rec, "attempts", 0) or 0)
	if attempts_val >= settings.OTP_MAX_ATTEMPTS:
		raise ValueError("Too many attempts")
	if not verify_otp(user_id, EmailOTPPurpose.FORGOT_PWD.value, otp, str(otp_rec.otp_hash)):
		await repository.increment_otp_attempts(db, str(otp_rec.id))
		raise ValueError("Invalid code")
	validate_password_policy(new_password)
	await repository.update_user_password(db, user_id, hash_password(new_password))
	await repository.mark_otp_used(db, str(otp_rec.id))
	await audit(db, "password.reset", actor_user_id=user_id)


async def change_password(db: AsyncSession, user_id: str, *, current_password: Optional[str], otp: Optional[str], new_password: str) -> None:
	user = await repository.get_user_by_id(db, user_id)
	if not user:
		raise ValueError("User not found")
	if current_password is not None:
		if not verify_password(current_password, str(user.password_hash)):
			raise ValueError("Current password invalid")
	elif otp:
		otp_rec = await repository.get_active_otp(db, user_id, EmailOTPPurpose.CHANGE_PWD)
		if not otp_rec or not verify_otp(user_id, EmailOTPPurpose.CHANGE_PWD.value, otp, str(otp_rec.otp_hash)):
			raise ValueError("Invalid code")
		await repository.mark_otp_used(db, str(otp_rec.id))
	else:
		raise ValueError("Provide current_password or otp")
	validate_password_policy(new_password)
	await repository.update_user_password(db, user_id, hash_password(new_password))
	await audit(db, "password.changed", actor_user_id=user_id)


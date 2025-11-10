"""OIDC auth scaffolding.

Provides:
- GET /auth/login -> returns provider authorize URL (frontend can redirect)
- GET /auth/callback -> placeholder that would validate state/code and set session

For now, we only echo the configuration pieces to demonstrate wiring.
"""
from urllib.parse import urlencode
from datetime import datetime, timezone
from typing import Optional, Any, cast
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User, UserRole, UserStatus, EmailOTPPurpose
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    LoginRequest,
    LoginResponse,
    ResendEmailOTPRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.modules.auth import service as auth_service  # Phase 2 service usage
from app.security.passwords import hash_password, verify_password, validate_password_policy
from app.security.jwt import create_access_token
from app.services.otp import generate_otp_and_hash, verify_otp
from app.services.mailer import send_email, render_otp_email
from app.services.audit import audit
from app.crud import users as users_crud
from app.crud import otps as otps_crud
from app.security.auth import get_oidc_config, verify_id_token

# naive in-memory rate limit (per-process) for OTP resends
_RESEND_BUCKET: dict[str, list[float]] = {}

router = APIRouter()


# Helper casters to appease static typing with SQLAlchemy Column/Enum attributes
def _str_attr(val: Any) -> str:
    if isinstance(val, str):
        return val
    # Enum value
    try:
        return cast(str, val.value)  # type: ignore[attr-defined]
    except Exception:
        return str(val)


def _int_attr(val: Any) -> int:
    try:
        return int(val)  # works for Python ints and SQLAlchemy instrumented ints
    except Exception:
        return 0


@router.get("/auth/login")
async def login_start() -> dict:
    cfg = get_oidc_config()
    if not cfg["issuer"] or not cfg["client_id"] or not cfg["redirect_uri"]:
        return {"enabled": False, "reason": "Missing OIDC config"}
    # In a real implementation, we'd fetch the provider's authorization_endpoint from
    # the OIDC discovery document. Here we scaffold a generic authorize URL.
    authorize_url = f"{cfg['issuer'].rstrip('/')}/authorize?" + urlencode({
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": cfg.get("scopes", "openid"),
        "state": "todo-state",
        "nonce": "todo-nonce",
    })
    return {"enabled": True, "authorize_url": authorize_url}


@router.get("/auth/callback")
async def login_callback(request: Request) -> dict:
    # Placeholder: in a full implementation, we'd exchange 'code' for tokens.
    # For scaffolding/testing, if an 'id_token' query param is present, verify it.
    params = dict(request.query_params)
    id_token = params.get("id_token")
    if id_token:
        try:
            claims = await verify_id_token(id_token)
            # In a real app, set a session cookie here tying the user to claims["sub"].
            return {"verified": True, "claims": {k: claims.get(k) for k in ("sub", "email", "name") if k in claims}}
        except HTTPException as e:
            raise e
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=401, detail=f"Invalid ID token: {e}")
    return {"received": params, "note": "Provide id_token to verify or implement token exchange"}


# -------- Email/password registration & OTP flows -------- #

@router.post("/auth/register", response_model=RegisterResponse)
async def register(data: RegisterRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    validate_password_policy(data.password)
    existing = await users_crud.get_by_email(db, data.email)
    if existing:
        return RegisterResponse(status="ok", message="If the email is new, you'll receive an OTP.")
    pwd_hash = hash_password(data.password)
    user = await users_crud.create_user(db, email=data.email, password_hash=pwd_hash, organization=data.organization)
    # create OTP for email verify
    otp, otp_hash, expires_at = generate_otp_and_hash(str(user.id), EmailOTPPurpose.EMAIL_VERIFY.value, settings.EMAIL_OTP_TTL_HOURS)
    await otps_crud.create_otp(db, str(user.id), EmailOTPPurpose.EMAIL_VERIFY, otp_hash, expires_at)
    subject, html = render_otp_email(otp, "email_verify")
    background.add_task(send_email, _str_attr(user.email), subject, html)
    await audit(db, "register.requested", actor_user_id=str(user.id), payload={"email": _str_attr(user.email)})
    return RegisterResponse(status="ok", message="Please check your email for the verification code.")


@router.post("/auth/verify-email", response_model=VerifyEmailResponse)
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    user = await users_crud.get_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status in (UserStatus.APPROVED, UserStatus.PENDING_ADMIN_APPROVAL):
        return VerifyEmailResponse(status=user.status.value, message="Already verified")
    try:
        new_status = await auth_service.verify_email(db, str(user.id), data.otp)
    except ValueError as e:
        msg = str(e)
        if msg == "No active OTP":
            raise HTTPException(status_code=400, detail="No active OTP; please resend")
        if msg == "Too many attempts":
            raise HTTPException(status_code=429, detail="Too many attempts; try later")
        if msg == "Invalid code":
            raise HTTPException(status_code=400, detail="Invalid code")
        raise HTTPException(status_code=400, detail=msg)
    return VerifyEmailResponse(status=new_status, message="Email verified")


@router.post("/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        token, role, user_id = await auth_service.authenticate_user(db, data.email, data.password)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("User not approved"):
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(access_token=token, expires_in=60*60, role=role)


@router.post("/auth/resend-email-otp")
async def resend_email_otp(data: ResendEmailOTPRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    user = await users_crud.get_by_email(db, data.email)
    if not user:
        return {"status": "ok"}
    try:
        otp_plain = await auth_service.issue_resend_email_otp(db, str(user.id))
    except ValueError as e:
        if str(e) == "Too many resend attempts":
            raise HTTPException(status_code=429, detail="Too many resend attempts; try later")
        raise HTTPException(status_code=400, detail=str(e))
    subject, html = render_otp_email(otp_plain, "email_verify")
    background.add_task(send_email, _str_attr(user.email), subject, html)
    return {"status": "ok"}


@router.post("/auth/request-change-password-otp")
async def request_change_password_otp(request: Request, db: AsyncSession = Depends(get_db)):
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    from app.security.jwt import decode_token
    try:
        claims = decode_token(auth.split()[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = claims.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    # Ensure UUID type for comparison with UUID(as_uuid=True) column
    try:
        uid_uuid = UUID(str(uid))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    user_res = await db.execute(select(User).where(User.id == uid_uuid))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await auth_service.request_change_password_otp(db, str(user.id))
    except ValueError as e:
        if str(e) == "Too many requests":
            raise HTTPException(status_code=429, detail="Too many requests; try later")
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    user = await users_crud.get_by_email(db, data.email)
    if not user:
        return {"status": "ok"}
    try:
        otp_plain = await auth_service.issue_forgot_password_otp(db, str(user.id))
    except ValueError as e:
        if str(e) == "Too many requests":
            raise HTTPException(status_code=429, detail="Too many requests; try later")
        raise HTTPException(status_code=400, detail=str(e))
    subject, html = render_otp_email(otp_plain, "forgot_pwd")
    background.add_task(send_email, _str_attr(user.email), subject, html)
    await audit(db, "forgot_password.requested", actor_user_id=str(user.id), payload={"email": _str_attr(user.email)})
    return {"status": "ok"}


@router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await users_crud.get_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await auth_service.reset_password_with_otp(db, str(user.id), data.otp, data.new_password)
    except ValueError as e:
        msg = str(e)
        if msg == "No active OTP":
            raise HTTPException(status_code=400, detail="No active OTP")
        if msg == "Too many attempts":
            raise HTTPException(status_code=429, detail="Too many attempts")
        if msg == "Invalid code":
            raise HTTPException(status_code=400, detail="Invalid code")
        if msg == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok"}


@router.post("/auth/change-password")
async def change_password(data: ChangePasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    from app.security.jwt import decode_token
    try:
        claims = decode_token(auth.split()[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = claims.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    try:
        uid_uuid = UUID(str(uid))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    try:
        await auth_service.change_password(
            db,
            str(uid_uuid),
            current_password=data.current_password,
            otp=data.otp,
            new_password=data.new_password,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "User not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "Current password invalid":
            raise HTTPException(status_code=400, detail=msg)
        if msg == "Invalid code":
            raise HTTPException(status_code=400, detail=msg)
        if msg == "Provide current_password or otp":
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok"}

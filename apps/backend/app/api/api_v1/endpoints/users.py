from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User
from app.utils.files import save_avatar

router = APIRouter()


def _get_current_user_from_bearer(request: Request, db: AsyncSession):
    # Simple helper; in full app use proper dependency
    from app.security.jwt import decode_token
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = decode_token(auth.split()[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return claims.get("sub")


@router.get("/users/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    uid = _get_current_user_from_bearer(request, db)
    res = await db.execute(select(User).where(User.id == uid))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "email": user.email,
        "organization": user.organization,
        "role": user.role.value,
        "status": user.status.value,
        "profile_image_url": user.profile_image_url,
        "last_login_at": user.last_login_at,
    }


@router.patch("/users/me/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    max_bytes = settings.AVATAR_MAX_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")
    uid = _get_current_user_from_bearer(request, db)
    storage_root = Path(__file__).resolve().parents[5] / "storage" / "uploads" / "avatars"
    storage_root.mkdir(parents=True, exist_ok=True)
    rel_url, path = save_avatar(storage_root, uid, content)
    # Persist on user
    await db.execute(
        User.__table__.update().where(User.id == uid).values(profile_image_url=f"/storage/{rel_url}")
    )
    await db.commit()
    return {"profile_image_url": f"/storage/{rel_url}", "message": "Avatar uploaded"}

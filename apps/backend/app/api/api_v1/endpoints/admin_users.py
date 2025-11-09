from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.session import get_db
from app.db.models import User, UserStatus, UserRole
from app.services.audit import audit

router = APIRouter()


def _require_admin(request: Request) -> str:
    from app.security.jwt import decode_token
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    claims = decode_token(auth.split()[1])
    if claims.get("role") != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin required")
    return claims.get("sub")


@router.get("/admin/users")
async def list_pending(status: str = "PENDING_ADMIN_APPROVAL", request: Request = None, db: AsyncSession = Depends(get_db)):
    _ = _require_admin(request)
    res = await db.execute(select(User).where(User.status == getattr(UserStatus, status)))
    users = res.scalars().all()
    return [{"id": str(u.id), "email": u.email, "organization": u.organization, "status": u.status.value} for u in users]


@router.post("/admin/users/{user_id}/approve")
async def approve(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    admin_id = _require_admin(request)
    await db.execute(update(User).where(User.id == user_id).values(status=UserStatus.APPROVED))
    await db.commit()
    await audit(db, "admin.user.approve", actor_user_id=admin_id, payload={"user_id": user_id})
    return {"status": "ok"}


@router.post("/admin/users/{user_id}/reject")
async def reject(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    admin_id = _require_admin(request)
    await db.execute(update(User).where(User.id == user_id).values(status=UserStatus.REJECTED))
    await db.commit()
    await audit(db, "admin.user.reject", actor_user_id=admin_id, payload={"user_id": user_id})
    return {"status": "ok"}

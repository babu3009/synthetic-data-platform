"""Users service layer.

Encapsulates user profile retrieval and avatar upload logic, keeping
FastAPI endpoints thin while making future extensions (auditing, caching,
validation) easier.

Edge cases handled:
- Missing/invalid bearer token -> 401
- User not found -> 404
- File size exceeds limit -> 400
- Unsupported image type (sniff failure) -> 400

Return shapes mirror legacy endpoints to preserve OpenAPI stability.
"""

from pathlib import Path
from fastapi import HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.security.jwt import decode_token
from app.utils.files import save_avatar, sniff_extension
from .repository import get_user_by_id, set_user_avatar_url
from uuid import UUID


def _extract_bearer_sub(request: Request) -> str:
	auth = request.headers.get("Authorization")
	if not auth or not auth.lower().startswith("bearer "):
		raise HTTPException(status_code=401, detail="Not authenticated")
	token = auth.split()[1]
	try:
		claims = decode_token(token)
	except Exception:
		raise HTTPException(status_code=401, detail="Invalid token")
	sub = claims.get("sub")
	if not sub:
		raise HTTPException(status_code=401, detail="Invalid token")
	return sub


async def get_profile(request: Request, db: AsyncSession):
	uid = _extract_bearer_sub(request)
	user = await get_user_by_id(db, uid)  # repository will coerce to UUID
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


async def upload_avatar(request: Request, file: UploadFile, db: AsyncSession):
	content = await file.read()
	max_bytes = settings.AVATAR_MAX_MB * 1024 * 1024
	if len(content) > max_bytes:
		raise HTTPException(status_code=400, detail="File too large")
	try:
		# quick validation via sniff without saving
		sniff_extension(content)
	except Exception:
		raise HTTPException(status_code=400, detail="Unsupported image type")

	uid = _extract_bearer_sub(request)
	storage_root = Path(__file__).resolve().parents[5] / "storage" / "uploads" / "avatars"
	storage_root.mkdir(parents=True, exist_ok=True)
	rel_url, _path = save_avatar(storage_root, uid, content)
	public_url = f"/storage/{rel_url}"
	await set_user_avatar_url(db, uid, public_url)
	return {"profile_image_url": public_url, "message": "Avatar uploaded"}


__all__ = ["get_profile", "upload_avatar"]

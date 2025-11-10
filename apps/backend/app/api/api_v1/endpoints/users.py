from fastapi import APIRouter, Depends, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.service import get_profile as service_get_profile, upload_avatar as service_upload_avatar

router = APIRouter()


@router.get("/users/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    return await service_get_profile(request, db)


@router.patch("/users/me/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await service_upload_avatar(request, file, db)

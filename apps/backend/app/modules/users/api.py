from fastapi import APIRouter

from app.api.api_v1.endpoints import users as legacy_users


router = APIRouter()

router.include_router(legacy_users.router, tags=["Users"])  # keep original tag

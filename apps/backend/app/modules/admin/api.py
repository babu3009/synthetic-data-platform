from fastapi import APIRouter

from app.api.api_v1.endpoints import admin_users as legacy_admin_users

router = APIRouter()

router.include_router(legacy_admin_users.router, tags=["Admin"])  # /api/v1/admin/users

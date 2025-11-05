from fastapi import APIRouter

from app.api.api_v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Additional routers will be added here as the API grows
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
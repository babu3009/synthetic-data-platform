from fastapi import APIRouter

from app.api.api_v1.endpoints import artifacts, health, projects, requests, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    sources.router, prefix="/projects/{project_id}/sources", tags=["sources"]
)
api_router.include_router(
    requests.router, prefix="/projects/{project_id}/requests", tags=["requests"]
)
api_router.include_router(artifacts.router, prefix="/requests", tags=["artifacts"])
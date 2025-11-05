from fastapi import APIRouter

from app.api.api_v1.endpoints import artifacts, health, projects, requests, sources, flat

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
api_router.include_router(flat.router, prefix="/flat", tags=["flat"])  # /api/v1/flat/preview
api_router.include_router(flat.req_router, prefix="/requests", tags=["requests"])  # /api/v1/requests/{id}:start
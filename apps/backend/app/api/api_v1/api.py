from fastapi import APIRouter

from app.api.api_v1.endpoints import artifacts, health, projects, requests, sources, flat, validate, webhooks, api_keys, auth, infer

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    sources.router, prefix="/projects/{project_id}/sources", tags=["sources"]
)
api_router.include_router(
    requests.router, prefix="/projects/{project_id}/requests", tags=["requests"]
)
api_router.include_router(
    api_keys.router, prefix="/projects/{project_id}/api-keys", tags=["api-keys"]
)
api_router.include_router(artifacts.router, prefix="/requests", tags=["artifacts"])
api_router.include_router(flat.router, prefix="/flat", tags=["flat"])  # /api/v1/flat/preview
api_router.include_router(flat.req_router, prefix="/requests", tags=["requests"])  # /api/v1/requests/{id}:start
api_router.include_router(validate.router, tags=["validate"])  # /api/v1/validate
api_router.include_router(webhooks.router, tags=["webhooks"])  # /api/v1/webhooks/run-status
api_router.include_router(auth.router, tags=["auth"])  # /api/v1/auth/login, /auth/callback
api_router.include_router(infer.router, prefix="/projects/{project_id}/infer", tags=["infer"])
api_router.include_router(infer.root_router, prefix="/infer", tags=["infer"])  # alias
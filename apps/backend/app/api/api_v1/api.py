from fastapi import APIRouter

# Legacy endpoints still imported for health/projects/api_keys/webhooks until modularized
from app.api.api_v1.endpoints import health, projects, api_keys, webhooks, entities

# Module routers (Phase 1 migration)
from app.modules.auth.api import router as auth_router
from app.modules.users.api import router as users_router
from app.modules.admin.api import router as admin_router
from app.modules.llm.api import router as llm_router
from app.modules.synth.api import router as synth_router
# storage module currently has no routes yet

api_router = APIRouter()

# Health & top-level project resources (still legacy)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(api_keys.router, prefix="/projects/{project_id}/api-keys", tags=["api-keys"])
api_router.include_router(entities.router, prefix="/projects/{project_id}/entities", tags=["entities"])
api_router.include_router(webhooks.router, tags=["webhooks"])  # /api/v1/webhooks/run-status

# Modular routers preserving existing prefixes & tags
api_router.include_router(auth_router, tags=["auth"])  # /api/v1/auth/*
api_router.include_router(users_router, tags=["Users"])  # /api/v1/users/*
api_router.include_router(admin_router, tags=["Admin"])  # /api/v1/admin/*
api_router.include_router(llm_router)  # infer, admin-llm, llm-settings prefixes preserved inside module
api_router.include_router(synth_router)  # sources, requests, artifacts, flat, validate

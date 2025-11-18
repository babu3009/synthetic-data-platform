from fastapi import APIRouter

from app.api.api_v1.endpoints import requests as legacy_requests
from app.api.api_v1.endpoints import sources as legacy_sources
from app.api.api_v1.endpoints import validate as legacy_validate
from app.api.api_v1.endpoints import flat as legacy_flat
from app.api.api_v1.endpoints import artifacts as legacy_artifacts

router = APIRouter()

# Preserve prefixes & tags used in the aggregator (api_v1/api.py)
router.include_router(legacy_sources.router, prefix="/projects/{project_id}/sources", tags=["sources"])
router.include_router(legacy_requests.router, prefix="/projects/{project_id}/requests", tags=["requests"])
router.include_router(legacy_artifacts.router, prefix="/requests", tags=["artifacts"])
router.include_router(legacy_flat.router, prefix="/flat", tags=["flat"])  # preview endpoints
router.include_router(legacy_flat.req_router, prefix="/projects/{project_id}/requests", tags=["requests"])  # job start endpoints
router.include_router(legacy_validate.router, tags=["validate"])  # validation endpoints

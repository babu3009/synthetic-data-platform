from fastapi import APIRouter

from app.api.api_v1.endpoints import infer as legacy_infer
from app.api.api_v1.endpoints import llm_admin as legacy_llm_admin
from app.api.api_v1.endpoints import llm_settings as legacy_llm_settings


router = APIRouter()

router.include_router(legacy_infer.router, prefix="/projects/{project_id}/infer", tags=["infer"])  # scoped infer
router.include_router(legacy_infer.root_router, prefix="/infer", tags=["infer"])  # alias
router.include_router(legacy_llm_admin.router, prefix="/admin/llm", tags=["admin-llm"])  # project_id as query
router.include_router(legacy_llm_settings.router, prefix="/projects/{project_id}/llm-settings", tags=["llm"])  # settings

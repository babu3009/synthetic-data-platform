from fastapi import APIRouter

# Phase 1: Wrap legacy endpoints to keep paths stable.
from app.api.api_v1.endpoints import auth as legacy_auth


router = APIRouter()

# Include all routes from the legacy auth router under the same tags/prefixes
router.include_router(legacy_auth.router, tags=["auth"])  # e.g., /api/v1/auth/*

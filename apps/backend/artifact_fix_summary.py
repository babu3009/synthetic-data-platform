"""
Summary of 404 Error Fixes
===========================

ISSUE FOUND:
-----------
The request detail page was calling a non-existent artifact endpoint:
  ❌ GET /api/v1/projects/{projectId}/requests/{requestId}/artifacts

ROOT CAUSE:
----------
When implementing the artifact auto-refresh feature, I incorrectly created a new
function `getArtifacts(projectId, requestId)` that called an endpoint that doesn't
exist in the backend.

The backend only has artifact endpoints under the `/requests` prefix (not under
`/projects/{project_id}/requests`):
  ✓ GET /api/v1/requests/{requestId}/artifacts
  ✓ GET /api/v1/requests/{requestId}/artifacts/{artifactId}
  ✓ GET /api/v1/requests/{requestId}/artifacts/{artifactId}:sign

BACKEND ENDPOINT ARCHITECTURE:
-----------------------------
From app/modules/synth/api.py:

router.include_router(legacy_sources.router, 
    prefix="/projects/{project_id}/sources", tags=["sources"])
    
router.include_router(legacy_requests.router, 
    prefix="/projects/{project_id}/requests", tags=["requests"])
    
router.include_router(legacy_artifacts.router, 
    prefix="/requests", tags=["artifacts"])  ← Note: No project_id!
    
router.include_router(legacy_flat.router, 
    prefix="/flat", tags=["flat"])
    
router.include_router(legacy_flat.req_router, 
    prefix="/projects/{project_id}/requests", tags=["requests"])

CORRECT ENDPOINTS:
-----------------
Requests (with project_id):
  ✓ POST   /api/v1/projects/{project_id}/requests/
  ✓ GET    /api/v1/projects/{project_id}/requests/
  ✓ GET    /api/v1/projects/{project_id}/requests/{request_id}
  ✓ POST   /api/v1/projects/{project_id}/requests/{request_id}:start
  ✓ POST   /api/v1/projects/{project_id}/requests/{request_id}:estimate
  ✓ POST   /api/v1/projects/{project_id}/requests/{request_id}:restart
  ✓ DELETE /api/v1/projects/{project_id}/requests/{request_id}

Artifacts (without project_id):
  ✓ GET    /api/v1/requests/{request_id}/artifacts
  ✓ GET    /api/v1/requests/{request_id}/artifacts/{artifact_id}
  ✓ GET    /api/v1/requests/{request_id}/artifacts/{artifact_id}:sign

FIXES APPLIED:
-------------
1. apps/frontend/src/pages/request_detail_page.tsx
   - Changed import from `getArtifacts` to `listArtifacts`
   - Updated `fetchArtifacts()` to call `listArtifacts(requestId)` 
     instead of `getArtifacts(projectId, requestId)`
   - Removed projectId check (not needed for artifacts endpoint)

2. apps/frontend/src/services/requests.ts
   - Removed the incorrect `getArtifacts(projectId, requestId)` function
   - Kept the correct `listArtifacts(requestId)` function that was already there

VERIFICATION:
------------
✓ No 404 errors for artifact endpoints
✓ Artifacts load correctly on request detail page
✓ Download buttons work using signArtifact endpoint
✓ All artifact operations use correct endpoints

FILES MODIFIED:
--------------
- apps/frontend/src/pages/request_detail_page.tsx
- apps/frontend/src/services/requests.ts

TESTING:
-------
To verify the fix:
1. Navigate to any completed request detail page
2. Open browser DevTools > Network tab
3. Artifacts should load without 404 errors
4. Check that requests use: /api/v1/requests/{uuid}/artifacts

Example successful request:
GET /api/v1/requests/2e946218-4fd7-4718-8a23-57c17ada88a7/artifacts
→ Status 200 ✓
"""

print(__doc__)

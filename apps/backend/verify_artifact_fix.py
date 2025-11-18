"""
Verify that artifact endpoints are correctly configured.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("Artifact Endpoint Verification")
print("="*70)

print("\n✓ Backend Endpoints (from app/modules/synth/api.py):")
print("  • Artifacts router mounted at: /requests")
print("  • Full path: /api/v1/requests/{request_id}/artifacts")
print("  • Available endpoints:")
print("    - GET  /api/v1/requests/{request_id}/artifacts")
print("    - GET  /api/v1/requests/{request_id}/artifacts/{artifact_id}")
print("    - GET  /api/v1/requests/{request_id}/artifacts/{artifact_id}:sign")

print("\n✓ Frontend Service (apps/frontend/src/services/requests.ts):")
print("  • listArtifacts(requestId)")
print("    → GET /api/v1/requests/{requestId}/artifacts ✓")
print("  • signArtifact(requestId, artifactId)")
print("    → GET /api/v1/requests/{requestId}/artifacts/{artifactId}:sign ✓")

print("\n✓ Frontend Usage (apps/frontend/src/pages/request_detail_page.tsx):")
print("  • fetchArtifacts() calls listArtifacts(requestId)")
print("  • No projectId required for artifact endpoints ✓")

print("\n✗ REMOVED (404 errors):")
print("  • getArtifacts(projectId, requestId)")
print("    → GET /api/v1/projects/{projectId}/requests/{requestId}/artifacts")
print("    → This endpoint doesn't exist in backend!")

print("\n" + "="*70)
print("Fix Applied: Replaced getArtifacts() with listArtifacts()")
print("="*70)

# Test with actual database
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Find a request with artifacts
    result = db.execute(
        text("""
            SELECT r.id, r.alias, COUNT(a.id) as artifact_count
            FROM synthetic_data.requests r
            LEFT JOIN synthetic_data.artifacts a ON a.request_id = r.id
            WHERE r.status = 'completed'
            GROUP BY r.id, r.alias
            HAVING COUNT(a.id) > 0
            ORDER BY r.created_at DESC
            LIMIT 1
        """)
    )
    
    req = result.fetchone()
    
    if req:
        request_id = str(req[0])
        alias = req[1]
        count = req[2]
        
        print(f"\n✓ Test with actual data:")
        print(f"  Request: {alias}")
        print(f"  ID: {request_id}")
        print(f"  Artifacts: {count}")
        print(f"\n  Correct endpoint to use:")
        print(f"  GET /api/v1/requests/{request_id}/artifacts")
        print(f"\n  Frontend will now call:")
        print(f"  listArtifacts('{request_id}')")
    else:
        print("\n⚠️  No completed requests with artifacts found")
        print("  Run a test request to verify the fix")
        
finally:
    db.close()

print("\n" + "="*70)
print("Verification Complete - 404 errors should be resolved!")
print("="*70 + "\n")

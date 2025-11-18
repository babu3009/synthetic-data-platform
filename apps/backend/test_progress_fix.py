"""
Quick test to verify progress tracking and data persistence fixes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal
from sqlalchemy import text

# Get a test project
db = SessionLocal()
try:
    # Find the first project
    result = db.execute(text('SELECT id, name FROM synthetic_data.projects LIMIT 1'))
    project = result.fetchone()
    
    if not project:
        print("❌ No projects found. Please run seed_db.py first.")
        sys.exit(1)
    
    project_id = str(project[0])
    project_name = project[1]
    
    print("\n" + "="*70)
    print("Progress Tracking Test")
    print("="*70)
    print(f"\nProject: {project_name}")
    print(f"ID: {project_id}")
    
    # Find a completed request with progress
    result = db.execute(
        text("""
            SELECT id, alias, status, 
                   params_json->>'progress' as progress,
                   created_at, started_at, finished_at
            FROM synthetic_data.requests
            WHERE project_id = :project_id
              AND status = 'completed'
              AND params_json ? 'progress'
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {'project_id': project_id}
    )
    
    req = result.fetchone()
    
    if req:
        print(f"\n✓ Found completed request with progress tracking:")
        print(f"  Alias: {req[1]}")
        print(f"  Status: {req[2]}")
        print(f"  Progress: {req[3]}%")
        print(f"  Created: {req[4]}")
        print(f"  Started: {req[5]}")
        print(f"  Finished: {req[6]}")
        
        # Count artifacts
        result = db.execute(
            text('SELECT COUNT(*) FROM synthetic_data.artifacts WHERE request_id = :id'),
            {'id': req[0]}
        )
        artifact_count = result.scalar()
        
        print(f"  Artifacts: {artifact_count}")
        
        print(f"\n🌐 Test in browser:")
        print(f"   http://localhost:3000/projects/{project_id}/requests/{req[0]}")
        print(f"\n✓ Expected behavior:")
        print(f"   • Progress bar shows {req[3]}%")
        print(f"   • Status badge is green (completed)")
        print(f"   • {artifact_count} artifact(s) in table with download buttons")
        print(f"   • All data loads immediately without refresh")
        
    else:
        # Create a test request for manual testing
        import json
        from uuid import uuid4
        
        test_alias = f"test-progress-{uuid4().hex[:8]}"
        
        result = db.execute(
            text("""
                INSERT INTO synthetic_data.requests 
                (id, project_id, type, alias, status, params_json)
                VALUES (
                    gen_random_uuid(), 
                    :project_id, 
                    'relational', 
                    :alias, 
                    'pending',
                    CAST(:params_json AS jsonb)
                )
                RETURNING id
            """).bindparams(
                project_id=project_id,
                alias=test_alias,
                params_json=json.dumps({
                    "schema": {
                        "tables": [{
                            "name": "test_progress_table",
                            "columns": [
                                {"name": "id", "type": "integer", "provider": {"type": "sequence", "start": 1}},
                                {"name": "name", "type": "varchar", "provider": "name"}
                            ],
                            "pk": ["id"],
                            "rowTarget": {"type": "absolute", "value": 50}
                        }]
                    },
                    "outputs": {"formats": ["csv"]},
                    "progress": 0
                })
            )
        )
        db.commit()
        request_id = str(result.fetchone()[0])
        
        print(f"\n✓ Created test request: {test_alias}")
        print(f"  Request ID: {request_id}")
        print(f"\n🌐 Test in browser:")
        print(f"   http://localhost:3000/projects/{project_id}/requests/{request_id}")
        print(f"\n✓ Testing steps:")
        print(f"   1. Click 'Start' button")
        print(f"   2. Watch progress bar update in real-time (0% → 100%)")
        print(f"   3. Verify status changes: pending → running → completed")
        print(f"   4. Confirm artifacts appear automatically")
        print(f"   5. DO NOT refresh - all data should load without page reload")
    
    print("\n" + "="*70)
    
finally:
    db.close()

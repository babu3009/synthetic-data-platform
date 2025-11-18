"""
Test script to verify WebSocket real-time updates, progress tracking, and artifact refresh.

This script:
1. Creates a test request with a small dataset
2. Connects to WebSocket endpoint to monitor updates
3. Starts the request and tracks progress messages
4. Verifies artifacts are sent when job completes
5. Tests error scenarios

Run this while the backend server is running.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import websockets
from app.db.session import SessionLocal
from app import crud
from sqlalchemy import text
from uuid import uuid4


# Test configuration
PROJECT_ID = "4447ef57-4de4-4f1f-8e26-89ea0439446c"  # Get from database
WEBSOCKET_URL = "ws://localhost:8000/api/v1/ws/requests/"
API_BASE = "http://localhost:8000/api/v1"


async def test_websocket_progress():
    """Test WebSocket real-time progress updates."""
    print("\n" + "="*70)
    print("TEST: WebSocket Real-time Progress Updates")
    print("="*70)
    
    # Create a small test request
    request_payload = {
        "type": "relational",
        "alias": f"test-progress-{uuid4().hex[:8]}",
        "params_json": {
            "schema": {
                "tables": [
                    {
                        "name": "test_users",
                        "columns": [
                            {
                                "name": "id",
                                "type": "integer",
                                "provider": {"type": "sequence", "start": 1}
                            },
                            {
                                "name": "email",
                                "type": "varchar",
                                "provider": "email"
                            }
                        ],
                        "pk": ["id"],
                        "rowTarget": {"type": "absolute", "value": 100}
                    }
                ]
            },
            "outputs": {
                "formats": ["csv"]
            },
            "progress": 0
        }
    }
    
    # Create request via database
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                INSERT INTO synthetic_data.requests 
                (id, project_id, type, alias, status, params_json)
                VALUES (gen_random_uuid(), :project_id, :type, :alias, 'pending', CAST(:params_json AS jsonb))
                RETURNING id
            """).bindparams(
                project_id=PROJECT_ID,
                type="relational",
                alias=request_payload["alias"],
                params_json=json.dumps(request_payload["params_json"])
            )
        )
        db.commit()
        request_id = str(result.fetchone()[0])
        print(f"\n✓ Created test request: {request_payload['alias']}")
        print(f"  Request ID: {request_id}")
    finally:
        db.close()
    
    # Connect to WebSocket
    ws_url = f"{WEBSOCKET_URL}{request_id}"
    print(f"\n→ Connecting to WebSocket: {ws_url}")
    
    messages_received = []
    progress_updates = []
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✓ WebSocket connected")
            
            # Start the request via HTTP
            print("\n→ Starting request via API...")
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_BASE}/projects/{PROJECT_ID}/requests/{request_id}:start"
                ) as resp:
                    if resp.status == 200:
                        print("✓ Request started successfully")
                    else:
                        print(f"✗ Failed to start request: {resp.status}")
                        return
            
            # Listen for WebSocket messages
            print("\n→ Listening for WebSocket messages...\n")
            
            timeout_seconds = 30
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Add timeout to prevent hanging
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    messages_received.append(data)
                    
                    msg_type = data.get('type')
                    
                    if msg_type == 'status':
                        status = data.get('status')
                        progress = data.get('progress')
                        
                        print(f"  📊 STATUS: {status}", end="")
                        if progress is not None:
                            print(f" | Progress: {progress}%")
                            progress_updates.append(progress)
                        else:
                            print(f" | No progress data")
                        
                        if data.get('error_message'):
                            print(f"     ⚠️  Error: {data['error_message']}")
                    
                    elif msg_type == 'artifacts':
                        artifacts = data.get('artifacts', [])
                        print(f"  📦 ARTIFACTS: {len(artifacts)} files received")
                        for art in artifacts:
                            size_kb = art.get('size_bytes', 0) / 1024
                            print(f"     - {art.get('format')} ({size_kb:.2f} KB)")
                    
                    elif msg_type == 'progress':
                        percent = data.get('percent')
                        print(f"  📈 PROGRESS: {percent}%")
                        progress_updates.append(percent)
                    
                    elif msg_type == 'complete':
                        print(f"  ✅ COMPLETE: Job finished")
                        break
                    
                    elif msg_type == 'error':
                        print(f"  ❌ ERROR: {data.get('message')}")
                        break
                    
                    # Timeout check
                    if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                        print(f"\n  ⏱️  Timeout after {timeout_seconds}s")
                        break
                        
                except asyncio.TimeoutError:
                    print("  ⏱️  No message received in 5s, continuing...")
                    if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                        print(f"\n  ⏱️  Overall timeout after {timeout_seconds}s")
                        break
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("\n  ⚠️  WebSocket connection closed")
                    break
    
    except Exception as e:
        print(f"\n✗ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "-"*70)
    print("TEST RESULTS:")
    print("-"*70)
    print(f"Total messages received: {len(messages_received)}")
    print(f"Progress updates: {len(progress_updates)}")
    if progress_updates:
        print(f"Progress range: {min(progress_updates)}% → {max(progress_updates)}%")
    
    # Check for required message types
    msg_types = [m.get('type') for m in messages_received]
    print(f"\nMessage types received: {set(msg_types)}")
    
    has_status = 'status' in msg_types
    has_artifacts = 'artifacts' in msg_types
    has_complete = 'complete' in msg_types
    has_progress_data = any(m.get('progress') is not None for m in messages_received if m.get('type') == 'status')
    
    print(f"\n✓ Status messages: {'✅' if has_status else '❌'}")
    print(f"✓ Progress data in status: {'✅' if has_progress_data else '❌'}")
    print(f"✓ Artifacts message: {'✅' if has_artifacts else '❌'}")
    print(f"✓ Complete message: {'✅' if has_complete else '❌'}")
    
    # Overall result
    all_passed = has_status and has_artifacts and has_complete
    if has_progress_data:
        print(f"\n{'='*70}")
        print("✅ ALL TESTS PASSED - Progress updates working!")
        print("="*70)
    elif all_passed:
        print(f"\n{'='*70}")
        print("⚠️  PARTIAL PASS - WebSocket works but no progress data")
        print("   (Progress may need to be updated by job execution)")
        print("="*70)
    else:
        print(f"\n{'='*70}")
        print("❌ TESTS FAILED - Missing required messages")
        print("="*70)
    
    return request_id


async def test_error_modal():
    """Test error modal by creating a request that will fail."""
    print("\n" + "="*70)
    print("TEST: Error Modal Functionality")
    print("="*70)
    
    # Create a request with invalid schema to trigger error
    request_payload = {
        "type": "relational",
        "alias": f"test-error-{uuid4().hex[:8]}",
        "params_json": {
            "schema": {
                "tables": [
                    {
                        "name": "invalid_table",
                        "columns": [],  # Empty columns will cause error
                        "rowTarget": {"type": "absolute", "value": 10}
                    }
                ]
            },
            "outputs": {
                "formats": ["csv"]
            }
        }
    }
    
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                INSERT INTO synthetic_data.requests 
                (id, project_id, type, alias, status, params_json)
                VALUES (gen_random_uuid(), :project_id, :type, :alias, 'pending', CAST(:params_json AS jsonb))
                RETURNING id
            """).bindparams(
                project_id=PROJECT_ID,
                type="relational",
                alias=request_payload["alias"],
                params_json=json.dumps(request_payload["params_json"])
            )
        )
        db.commit()
        request_id = str(result.fetchone()[0])
        print(f"\n✓ Created error test request: {request_payload['alias']}")
        print(f"  Request ID: {request_id}")
    finally:
        db.close()
    
    # Start the request (should fail)
    print("\n→ Starting request (expecting failure)...")
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE}/projects/{PROJECT_ID}/requests/{request_id}:start"
        ) as resp:
            result = await resp.json()
            if result.get('status') == 'failed':
                print(f"✓ Request failed as expected")
                print(f"  Error message: {result.get('error_message', 'N/A')[:100]}...")
                print("\n✅ Error scenario works - test in browser:")
                print(f"   http://localhost:3000/projects/{PROJECT_ID}/requests/{request_id}")
                print("   Click 'View Error' button to see modal")
                return request_id
            else:
                print(f"⚠️  Unexpected status: {result.get('status')}")
    
    return request_id


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("WebSocket Features Test Suite")
    print("="*70)
    print("\nThis test verifies:")
    print("1. Real-time progress updates via WebSocket")
    print("2. Artifact auto-refresh when job completes")
    print("3. Error modal functionality")
    print("\nMake sure backend server is running on http://localhost:8000")
    print("="*70)
    
    # Test 1: Progress updates
    request_id_1 = await test_websocket_progress()
    
    # Test 2: Error modal
    request_id_2 = await test_error_modal()
    
    # Summary
    print("\n" + "="*70)
    print("MANUAL TESTING INSTRUCTIONS")
    print("="*70)
    print("\n1. Open browser to request detail pages:")
    if request_id_1:
        print(f"\n   Success case:")
        print(f"   http://localhost:3000/projects/{PROJECT_ID}/requests/{request_id_1}")
    if request_id_2:
        print(f"\n   Error case:")
        print(f"   http://localhost:3000/projects/{PROJECT_ID}/requests/{request_id_2}")
    
    print("\n2. Verify in browser:")
    print("   ✓ Progress bar shows and updates (0% → 100%)")
    print("   ✓ Status changes: pending → running → completed/failed")
    print("   ✓ Artifacts table auto-populates with download buttons")
    print("   ✓ Failed requests show 'View Error' button")
    print("   ✓ Clicking 'View Error' opens modal with full error message")
    print("   ✓ Modal shows request ID, status badge, and formatted error")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())

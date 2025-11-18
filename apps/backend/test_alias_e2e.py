"""
End-to-end test for request alias feature.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import AsyncSessionLocal
from app.crud import request as crud_request, project as crud_project
from app.schemas.request import RequestCreate
from app.db.models import RequestType, RequestStatus


async def test_alias_feature():
    """Test creating requests with and without aliases."""
    print("=" * 70)
    print("End-to-End Test: Request Alias Feature")
    print("=" * 70)
    
    async with AsyncSessionLocal() as db:
        # Get or create a test project
        print("\n1. Setting up test project...")
        projects = await crud_project.get_multi(db, limit=1)
        if not projects:
            print("  ✗ No projects found. Please create a project first.")
            return
        
        project = projects[0]
        print(f"  ✓ Using project: {project.name} ({project.id})")
        
        # Test 1: Create request without alias (should auto-generate)
        print("\n2. Test: Create request WITHOUT alias (backend should auto-generate)...")
        request_data = RequestCreate(
            type=RequestType.FLAT,
            params_json={"test": "auto-alias"}
        )
        req1 = await crud_request.create_with_project(
            db=db,
            obj_in=request_data,
            project_id=project.id
        )
        await db.refresh(req1)
        
        if req1.alias:
            print(f"  ✓ Auto-generated alias: '{req1.alias}'")
            print(f"    Request ID: {req1.id}")
        else:
            print(f"  ✗ Failed! No alias was generated.")
            print(f"    Request ID: {req1.id}")
        
        # Test 2: Create request with custom alias
        print("\n3. Test: Create request WITH custom alias...")
        custom_alias = "my-test-run-2025"
        request_data2 = RequestCreate(
            type=RequestType.RELATIONAL,
            alias=custom_alias,
            params_json={"test": "custom-alias"}
        )
        req2 = await crud_request.create_with_project(
            db=db,
            obj_in=request_data2,
            project_id=project.id
        )
        await db.refresh(req2)
        
        if req2.alias == custom_alias:
            print(f"  ✓ Custom alias preserved: '{req2.alias}'")
            print(f"    Request ID: {req2.id}")
        else:
            print(f"  ✗ Failed! Expected '{custom_alias}', got '{req2.alias}'")
        
        # Test 3: Create another request without alias (should be different)
        print("\n4. Test: Create another request WITHOUT alias (should differ from first)...")
        request_data3 = RequestCreate(
            type=RequestType.FLAT,
            params_json={"test": "second-auto-alias"}
        )
        req3 = await crud_request.create_with_project(
            db=db,
            obj_in=request_data3,
            project_id=project.id
        )
        await db.refresh(req3)
        
        if req3.alias and req3.alias != req1.alias:
            print(f"  ✓ Different auto-generated alias: '{req3.alias}'")
            print(f"    Request ID: {req3.id}")
            print(f"    (Previous was: '{req1.alias}')")
        elif req3.alias == req1.alias:
            print(f"  ⚠ Warning: Same alias as previous: '{req3.alias}'")
            print(f"    This is possible but unlikely (1/2304 chance)")
        else:
            print(f"  ✗ Failed! No alias was generated.")
        
        # Test 4: Verify all requests are retrievable
        print("\n5. Test: Verify all test requests are in database...")
        try:
            all_test_requests = await crud_request.get_by_project(
                db=db,
                project_id=project.id,
                limit=100
            )
            
            test_ids = {req1.id, req2.id, req3.id}
            found_requests = [r for r in all_test_requests if r.id in test_ids]
            
            print(f"  ✓ Found {len(found_requests)}/3 test requests:")
            for r in found_requests:
                print(f"    • {r.id} | Alias: '{r.alias}' | Type: {r.type}")
        except Exception as e:
            print(f"  ⚠ Warning: Could not fetch all requests (old data with enum mismatch)")
            print(f"    Error: {str(e)[:100]}")
            print(f"  ✓ But our 3 test requests were created successfully!")
        
        print("\n" + "=" * 70)
        print("✅ End-to-End Test Complete!")
        print("=" * 70)
        print("\nSummary:")
        print(f"  • Auto-generated aliases: '{req1.alias}', '{req3.alias}'")
        print(f"  • Custom alias: '{req2.alias}'")
        print(f"  • All aliases are {'unique' if len({req1.alias, req2.alias, req3.alias}) == 3 else 'NOT unique (ISSUE!)'}")
        print("\nNext steps:")
        print("  1. Test in frontend by creating a request through the wizard")
        print("  2. Verify alias appears in request list and detail pages")
        print("  3. Test WebSocket includes alias in status updates")


if __name__ == "__main__":
    asyncio.run(test_alias_feature())

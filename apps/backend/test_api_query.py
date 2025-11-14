"""
Test script to verify projects API query logic without running the full server.
"""
import asyncio
import os
from uuid import UUID
from sqlalchemy import select, text

# CRITICAL: Remove PYTEST_CURRENT_TEST to prevent test schema usage
if "PYTEST_CURRENT_TEST" in os.environ:
    del os.environ["PYTEST_CURRENT_TEST"]

from app.db.session import AsyncSessionLocal
from app.db.models import Project, ProjectMember
from app.db.base import SCHEMA_NAME

async def test_projects_query():
    """Test the query used by GET /api/v1/projects/ endpoint."""
    # User ID for babu3009@gmail.com
    user_id = UUID("810914cd-5f38-4270-be5f-3ee9aa942f7f")
    
    async with AsyncSessionLocal() as db:
        # First, check what schema is being used
        print("=== Schema Check ===")
        print(f"SCHEMA_NAME constant: {SCHEMA_NAME}")
        result = await db.execute(text("SHOW search_path"))
        search_path = result.scalar()
        print(f"Current search_path: {search_path}")
        
        # Check for Students project member using raw SQL
        print("\n=== Raw SQL Query ===")
        result = await db.execute(text("""
            SELECT p.id, p.name, pm.user_id, pm.role 
            FROM synthetic_data.projects p 
            JOIN synthetic_data.project_members pm ON pm.project_id = p.id 
            WHERE p.name = 'Students' AND pm.user_id = :user_id
        """), {"user_id": user_id})
        rows = result.fetchall()
        print(f"Found {len(rows)} row(s) with raw SQL:")
        for row in rows:
            print(f"  - Project ID: {row[0]}, Name: {row[1]}, User ID: {row[2]}, Role: {row[3]}")
        
        # Now test with ORM query
        print(f"\n=== ORM Query ===")
        print(f"Testing projects query for user: {user_id}")
        
        # This is the actual query from projects.py endpoint (lines 130-135)
        q = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .offset(0)
            .limit(100)
        )
        res = await db.execute(q)
        projects = res.scalars().all()
        
        print(f"Found {len(projects)} project(s) with ORM:")
        for proj in projects:
            print(f"  - ID: {proj.id}")
            print(f"    Name: {proj.name}")
            print(f"    Owner User ID: {proj.owner_user_id}")
            print(f"    Created: {proj.created_at}")
        
        if len(projects) == 0:
            print("\n❌ No projects found with ORM! This means the API would return empty list.")
            print("   Possible issue: ORM using different schema or incorrect table metadata.")
        else:
            print(f"\n✅ API would return {len(projects)} project(s)!")

if __name__ == "__main__":
    asyncio.run(test_projects_query())

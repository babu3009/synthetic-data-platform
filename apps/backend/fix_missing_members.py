import asyncio
import os
from uuid import UUID
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.db.models import ProjectMember, ProjectRole

async def fix_missing_members():
    # Ensure we're using the production schema, not test schema
    os.environ.setdefault('DB_SCHEMA', 'synthetic_data')
    
    async with AsyncSessionLocal() as db:
        # Set schema for this session explicitly
        await db.execute(text("SET search_path TO synthetic_data, public"))
        
        # Find projects without members but with owner_user_id
        result = await db.execute(text("""
            SELECT p.id, p.name, p.owner_user_id, u.email 
            FROM synthetic_data.projects p
            LEFT JOIN synthetic_data.project_members pm ON p.id = pm.project_id AND p.owner_user_id = pm.user_id
            JOIN synthetic_data.users u ON p.owner_user_id = u.id
            WHERE pm.id IS NULL AND p.owner_user_id IS NOT NULL
        """))
        projects_without_members = result.fetchall()
        
        if not projects_without_members:
            print("All projects have proper owner members!")
            return
        
        print(f"Found {len(projects_without_members)} projects without owner members:")
        for proj in projects_without_members:
            print(f"  - Project: {proj[1]} (ID: {proj[0]}), Owner: {proj[3]} (ID: {proj[2]})")
        
        print("\nAdding missing owner members...")
        for proj in projects_without_members:
            # Insert directly with SQL to avoid ORM schema issues
            await db.execute(text("""
                INSERT INTO synthetic_data.project_members (id, project_id, user_id, role)
                VALUES (gen_random_uuid(), :project_id, :user_id, :role)
            """), {
                "project_id": proj[0],
                "user_id": proj[2],
                "role": "OWNER"
            })
            print(f"  ✓ Added OWNER member for project '{proj[1]}' and user '{proj[3]}'")
        
        await db.commit()
        print("\n✅ All missing owner members have been added!")

if __name__ == "__main__":
    asyncio.run(fix_missing_members())

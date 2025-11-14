import asyncio
import os
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def check_database():
    async with AsyncSessionLocal() as db:
        # Check users
        print("=== USERS ===")
        result = await db.execute(text("SELECT id, email, role, status FROM synthetic_data.users ORDER BY email LIMIT 10"))
        users = result.fetchall()
        for user in users:
            print(f"ID: {user[0]}, Email: {user[1]}, Role: {user[2]}, Status: {user[3]}")
        
        print("\n=== PROJECTS ===")
        result = await db.execute(text("SELECT id, name, owner_user_id, created_at FROM synthetic_data.projects ORDER BY created_at DESC LIMIT 10"))
        projects = result.fetchall()
        for proj in projects:
            print(f"ID: {proj[0]}, Name: {proj[1]}, Owner User ID: {proj[2]}, Created: {proj[3]}")
        
        print("\n=== PROJECT MEMBERS ===")
        result = await db.execute(text("SELECT pm.id, pm.project_id, pm.user_id, pm.role, p.name, u.email FROM synthetic_data.project_members pm JOIN synthetic_data.projects p ON pm.project_id = p.id LEFT JOIN synthetic_data.users u ON pm.user_id = u.id ORDER BY pm.created_at DESC LIMIT 10"))
        members = result.fetchall()
        for member in members:
            print(f"Member ID: {member[0]}, Project: {member[4]}, User: {member[5]}, Role: {member[3]}")
        
        # Check specifically for Students project
        print("\n=== STUDENTS PROJECT MEMBER ===")
        result = await db.execute(text("SELECT pm.id, p.name, u.email, pm.role FROM synthetic_data.project_members pm JOIN synthetic_data.projects p ON pm.project_id = p.id JOIN synthetic_data.users u ON pm.user_id = u.id WHERE p.name = 'Students'"))
        students_member = result.fetchone()
        if students_member:
            print(f"✓ Found: Member ID {students_member[0]}, Project '{students_member[1]}', User '{students_member[2]}', Role {students_member[3]}")
        else:
            print("✗ No member found for Students project")

if __name__ == "__main__":
    asyncio.run(check_database())

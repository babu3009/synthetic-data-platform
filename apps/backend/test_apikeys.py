import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check_api_keys():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT id, name, scopes 
            FROM synthetic_data.api_keys 
            WHERE project_id = 'e4fedd62-7529-4bf2-95ca-10b98093bcff' 
            LIMIT 5
        """))
        rows = result.fetchall()
        print(f"Found {len(rows)} API keys")
        for r in rows:
            print(f"  ID: {r[0]}, Name: {r[1]}, Scopes: {r[2]}, Type: {type(r[2])}")

if __name__ == "__main__":
    asyncio.run(check_api_keys())

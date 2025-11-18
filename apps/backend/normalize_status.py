import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def normalize():
    async with AsyncSessionLocal() as db:
        # Update all uppercase status values to lowercase
        result = await db.execute(text("""
            UPDATE synthetic_data.requests
            SET status = LOWER(status)
            WHERE status != LOWER(status)
        """))
        await db.commit()
        print(f'Normalized {result.rowcount} request status values to lowercase')

asyncio.run(normalize())

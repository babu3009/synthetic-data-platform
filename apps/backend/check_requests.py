import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(
            'SELECT id, status, alias FROM synthetic_data.requests ORDER BY created_at DESC LIMIT 5'
        ))
        rows = result.fetchall()
        print('Recent requests:')
        for row in rows:
            print(f'  {row[0]} - {row[1]} - {row[2]}')

asyncio.run(check())

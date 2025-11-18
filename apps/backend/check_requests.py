import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(
            "SELECT id, status, alias, started_at, finished_at FROM synthetic_data.requests WHERE id = 'a2860c2b-9d47-4db9-b988-8e5362efc54a'"
        ))
        row = result.fetchone()
        if row:
            print(f'ID: {row[0]}')
            print(f'Alias: {row[2]}')
            print(f'Status: {row[1]}')
            print(f'Started: {row[3]}')
            print(f'Finished: {row[4]}')
        else:
            print('Request not found')

asyncio.run(check())

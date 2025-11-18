"""Delete all pending requests from the database."""
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def delete_pending_requests():
    """Delete all pending requests."""
    async with AsyncSessionLocal() as db:
        # Delete all pending requests using raw SQL
        stmt = text("DELETE FROM synthetic_data.requests WHERE status = 'pending'")
        result = await db.execute(stmt)
        await db.commit()
        print(f"Deleted {result.rowcount} pending requests")
        return result.rowcount


if __name__ == "__main__":
    count = asyncio.run(delete_pending_requests())
    print(f"Successfully deleted {count} pending request(s)")

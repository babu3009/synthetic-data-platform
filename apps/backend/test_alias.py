"""
Test the alias functionality for requests.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def check_aliases():
    """Check if alias column exists and show recent requests."""
    print("=" * 60)
    print("Testing Request Alias Feature")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # Check if alias column exists
        print("\n1. Checking if alias column exists...")
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'synthetic_data'
              AND table_name = 'requests'
              AND column_name = 'alias'
        """))
        column_info = result.fetchone()
        if column_info:
            print(f"  ✓ Alias column exists: {column_info[0]} ({column_info[1]}, nullable={column_info[2]})")
        else:
            print("  ✗ Alias column not found!")
            return
        
        # Check for index
        print("\n2. Checking for index on alias column...")
        result = await db.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'synthetic_data'
              AND tablename = 'requests'
              AND indexname LIKE '%alias%'
        """))
        index = result.fetchone()
        if index:
            print(f"  ✓ Index exists: {index[0]}")
        else:
            print("  ⚠ No index found on alias column")
        
        # Show recent requests
        print("\n3. Recent requests with aliases:")
        result = await db.execute(text("""
            SELECT id, alias, type, status, created_at
            FROM synthetic_data.requests
            ORDER BY created_at DESC
            LIMIT 10
        """))
        rows = result.fetchall()
        
        if rows:
            print(f"\n  Found {len(rows)} request(s):")
            for r in rows:
                alias_display = f"'{r[1]}'" if r[1] else "NULL"
                print(f"    • {r[0]} | Alias: {alias_display} | Type: {r[2]} | Status: {r[3]}")
        else:
            print("  No requests found in database")
        
        print("\n" + "=" * 60)
        print("✅ Alias feature verification complete!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_aliases())

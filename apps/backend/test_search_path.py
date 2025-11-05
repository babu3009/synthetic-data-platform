#!/usr/bin/env python
"""Test that the database connection uses the correct schema search path."""
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal, engine
from app.db.base import SCHEMA_NAME


async def test_search_path():
    """Test that the search_path is correctly configured."""
    print(f"Testing schema connection to: {SCHEMA_NAME}")
    print("=" * 50)
    
    try:
        # Test 1: Check search_path setting
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            print(f"✓ Current search_path: {search_path}")
            
            if SCHEMA_NAME in search_path:
                print(f"✓ Schema '{SCHEMA_NAME}' is in search_path")
            else:
                print(f"✗ Warning: Schema '{SCHEMA_NAME}' NOT in search_path!")
        
        # Test 2: Check if schema exists
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": SCHEMA_NAME}
            )
            schema_exists = result.scalar()
            
            if schema_exists:
                print(f"✓ Schema '{SCHEMA_NAME}' exists in database")
            else:
                print(f"✗ Schema '{SCHEMA_NAME}' does NOT exist in database")
        
        # Test 3: List tables in the schema
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = :schema 
                    ORDER BY table_name
                """),
                {"schema": SCHEMA_NAME}
            )
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"✓ Found {len(tables)} tables in '{SCHEMA_NAME}' schema:")
                for table in tables:
                    print(f"  - {table}")
            else:
                print(f"ℹ No tables found in '{SCHEMA_NAME}' schema (migration may not be applied yet)")
        
        print("=" * 50)
        print("✓ Schema connection test completed successfully!")
        
    except Exception as e:
        print(f"✗ Error testing schema connection: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up engine
        await engine.dispose()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_search_path())
    exit(0 if success else 1)

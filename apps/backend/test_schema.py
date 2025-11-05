"""
Test script to verify schema configuration and database connectivity.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal, engine
from app.db.base import SCHEMA_NAME
from app.db import models


async def test_schema_creation():
    """Test that schema can be created and accessed."""
    print("=" * 60)
    print("Testing Schema Configuration")
    print("=" * 60)
    print(f"\nConfigured Schema: {SCHEMA_NAME}")
    
    try:
        # Create schema if it doesn't exist
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}"))
            print(f"✓ Schema '{SCHEMA_NAME}' created/verified")
        
        # Test connection
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT current_schema()"))
            current_schema = result.scalar()
            print(f"✓ Connected to database")
            print(f"  Current schema: {current_schema}")
            
            # Check if our schema exists
            result = await session.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ), {"schema": SCHEMA_NAME})
            schema_exists = result.scalar()
            
            if schema_exists:
                print(f"✓ Schema '{SCHEMA_NAME}' exists in database")
            else:
                print(f"✗ Schema '{SCHEMA_NAME}' not found")
                return False
            
            # Check search path
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            print(f"  Search path: {search_path}")
        
        print("\n" + "=" * 60)
        print("Schema Test PASSED ✓")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\n" + "=" * 60)
        print("Schema Test FAILED ✗")
        print("=" * 60)
        return False


async def test_model_metadata():
    """Test that models have correct schema configuration."""
    print("\n" + "=" * 60)
    print("Testing Model Metadata")
    print("=" * 60)
    
    model_classes = [
        models.Project,
        models.Source,
        models.Request,
        models.Config,
        models.Artifact,
        models.ApiKey,
        models.AuditEvent,
    ]
    
    all_correct = True
    for model_class in model_classes:
        table = model_class.__table__
        table_schema = table.schema
        table_name = table.name
        
        if table_schema == SCHEMA_NAME:
            print(f"✓ {model_class.__name__}: {table_schema}.{table_name}")
        else:
            print(f"✗ {model_class.__name__}: schema mismatch (expected '{SCHEMA_NAME}', got '{table_schema}')")
            all_correct = False
    
    # Check foreign keys
    print("\nForeign Key Schemas:")
    for model_class in model_classes:
        table = model_class.__table__
        for fk in table.foreign_keys:
            fk_column = fk.column
            fk_table = fk_column.table
            fk_schema = fk_table.schema
            print(f"  {model_class.__name__}.{fk.parent.name} -> {fk_schema}.{fk_table.name}.{fk_column.name}")
            if fk_schema != SCHEMA_NAME:
                print(f"    ✗ Schema mismatch!")
                all_correct = False
    
    print("\n" + "=" * 60)
    if all_correct:
        print("Model Metadata Test PASSED ✓")
    else:
        print("Model Metadata Test FAILED ✗")
    print("=" * 60)
    
    return all_correct


async def main():
    """Run all tests."""
    print("\n🧪 Starting Schema Configuration Tests\n")
    
    # Test model metadata (doesn't require DB connection)
    metadata_ok = await test_model_metadata()
    
    # Test schema creation (requires DB connection)
    try:
        schema_ok = await test_schema_creation()
    except Exception as e:
        print(f"\n⚠️  Could not test database connection: {e}")
        print("   Make sure PostgreSQL is running (docker-compose up -d)")
        schema_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Model Metadata: {'✓ PASS' if metadata_ok else '✗ FAIL'}")
    print(f"Schema Creation: {'✓ PASS' if schema_ok else '⚠ SKIP (no DB connection)'}")
    print("=" * 60)
    
    if metadata_ok:
        print("\n✅ Schema configuration is correct!")
        print(f"   All tables will be created in schema: {SCHEMA_NAME}")
        if not schema_ok:
            print("\n📝 Next steps:")
            print("   1. Start PostgreSQL: cd ../../infra && docker-compose up -d")
            print("   2. Run this test again")
            print("   3. Generate migration: alembic revision --autogenerate -m 'Add schema'")
            print("   4. Apply migration: alembic upgrade head")
    else:
        print("\n❌ Schema configuration has errors - please review")
    
    await engine.dispose()
    return metadata_ok and schema_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

"""
Apply error fields migration to requests table.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db.session import engine
from app.db.base import SCHEMA_NAME


async def apply_error_fields_migration():
    """Add error_message and error_traceback columns to requests table."""
    print("=" * 60)
    print("Applying Request Error Fields Migration")
    print("=" * 60)
    print(f"\nSchema: {SCHEMA_NAME}")
    
    try:
        async with engine.begin() as conn:
            # Add error_message column
            print("\n1. Adding error_message column to requests table...")
            await conn.execute(text(f"""
                ALTER TABLE {SCHEMA_NAME}.requests
                ADD COLUMN IF NOT EXISTS error_message TEXT
            """))
            print("  ✓ error_message column added")
            
            # Add error_traceback column
            print("\n2. Adding error_traceback column to requests table...")
            await conn.execute(text(f"""
                ALTER TABLE {SCHEMA_NAME}.requests
                ADD COLUMN IF NOT EXISTS error_traceback TEXT
            """))
            print("  ✓ error_traceback column added")
            
            # Update alembic version
            print("\n3. Updating Alembic version...")
            await conn.execute(text(f"""
                UPDATE {SCHEMA_NAME}.alembic_version
                SET version_num = '2025_11_18_0001'
                WHERE version_num = '2025_11_16_0001'
            """))
            print("  ✓ version updated")
            
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 60)
        print("\nThe requests table now has:")
        print("  • error_message column (TEXT, nullable)")
        print("  • error_traceback column (TEXT, nullable)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(apply_error_fields_migration())
    sys.exit(0 if success else 1)

"""
Apply alias column migration to requests table.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.db.session import engine
from app.db.base import SCHEMA_NAME


async def apply_alias_migration():
    """Add alias column to requests table."""
    print("=" * 60)
    print("Applying Request Alias Migration")
    print("=" * 60)
    print(f"\nSchema: {SCHEMA_NAME}")
    
    try:
        async with engine.begin() as conn:
            # Add alias column
            print("\n1. Adding alias column to requests table...")
            await conn.execute(text(f"""
                ALTER TABLE {SCHEMA_NAME}.requests
                ADD COLUMN IF NOT EXISTS alias VARCHAR(255)
            """))
            print("  ✓ alias column added")
            
            # Create index
            print("\n2. Creating index on alias column...")
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{SCHEMA_NAME}_requests_alias
                ON {SCHEMA_NAME}.requests(alias)
            """))
            print("  ✓ index created")
            
            # Update alembic version
            print("\n3. Updating Alembic version...")
            await conn.execute(text(f"""
                UPDATE {SCHEMA_NAME}.alembic_version
                SET version_num = '2025_11_16_0001'
                WHERE version_num = '2025_11_15_0240'
            """))
            print("  ✓ version updated")
            
        print("\n" + "=" * 60)
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 60)
        print("\nThe requests table now has:")
        print("  • alias column (VARCHAR(255), nullable)")
        print("  • index on alias column")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(apply_alias_migration())
    sys.exit(0 if success else 1)

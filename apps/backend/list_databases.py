"""
List all available databases on the PostgreSQL server.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def list_databases():
    """List all databases on the server."""
    print("=" * 60)
    print("PostgreSQL Server Information")
    print("=" * 60)
    
    print(f"\nServer:   {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
    print(f"User:     {settings.POSTGRES_USER}")
    
    # Connect to postgres database
    default_db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    
    try:
        engine = create_async_engine(default_db_url, echo=False)
        
        async with engine.connect() as conn:
            # Get PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"\nPostgreSQL: {version.split(',')[0]}")
            
            # List all databases
            result = await conn.execute(
                text("""
                    SELECT datname
                    FROM pg_database 
                    WHERE datistemplate = false
                    ORDER BY datname
                """)
            )
            
            databases = result.fetchall()
            
            print(f"\nAvailable Databases:")
            print("-" * 60)
            for db in databases:
                print(f"  • {db[0]}")
            
            print("\n" + "=" * 60)
            print(f"Looking for database: '{settings.POSTGRES_DB}'")
            
            # Check if our database exists with exact match
            result = await conn.execute(
                text("SELECT datname FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.POSTGRES_DB}
            )
            exact_match = result.scalar()
            
            if exact_match:
                print(f"✓ Database '{settings.POSTGRES_DB}' found (exact match)")
            else:
                print(f"✗ Database '{settings.POSTGRES_DB}' not found")
                
                # Try case-insensitive search
                result = await conn.execute(
                    text("SELECT datname FROM pg_database WHERE LOWER(datname) = LOWER(:dbname)"),
                    {"dbname": settings.POSTGRES_DB}
                )
                case_insensitive = result.scalar()
                
                if case_insensitive:
                    print(f"⚠ Found similar database: '{case_insensitive}' (case mismatch)")
                    print(f"  Update .env to use: POSTGRES_DB={case_insensitive}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(list_databases())

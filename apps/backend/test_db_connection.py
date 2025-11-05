"""
Test database connection and create database if it doesn't exist.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def test_connection():
    """Test connection to PostgreSQL server and create database if needed."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    # Display configuration
    print(f"\nServer:   {settings.POSTGRES_SERVER}")
    print(f"Port:     {settings.POSTGRES_PORT}")
    print(f"User:     {settings.POSTGRES_USER}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"Password: {'*' * len(settings.POSTGRES_PASSWORD)}")
    
    # Try to connect to postgres database first (which always exists)
    default_db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    
    try:
        print(f"\n1. Connecting to server (postgres database)...")
        engine = create_async_engine(default_db_url, echo=False, isolation_level="AUTOCOMMIT")
        
        async with engine.connect() as conn:
            # Check PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ Connected successfully!")
            print(f"  PostgreSQL version: {version.split(',')[0]}")
            
            # Check if our database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.POSTGRES_DB}
            )
            db_exists = result.scalar()
            
            if db_exists:
                print(f"\n2. Database '{settings.POSTGRES_DB}' exists ✓")
            else:
                print(f"\n2. Database '{settings.POSTGRES_DB}' does not exist")
                print(f"   Creating database '{settings.POSTGRES_DB}'...")
                
                # Create the database
                await conn.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
                print(f"✓ Database created successfully!")
        
        await engine.dispose()
        
        # Now try to connect to our database
        print(f"\n3. Connecting to '{settings.POSTGRES_DB}' database...")
        app_engine = create_async_engine(settings.get_database_url(), echo=False)
        
        async with app_engine.connect() as conn:
            result = await conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            print(f"✓ Connected to database: {current_db}")
            
            # List existing schemas
            result = await conn.execute(
                text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
            )
            schemas = [row[0] for row in result.fetchall()]
            print(f"\n4. Existing schemas: {', '.join(schemas)}")
        
        await app_engine.dispose()
        
        print("\n" + "=" * 60)
        print("✅ DATABASE CONNECTION TEST PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Generate migration: alembic revision --autogenerate -m 'Add schema'")
        print("  2. Apply migration: alembic upgrade head")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\n" + "=" * 60)
        print("❌ DATABASE CONNECTION TEST FAILED")
        print("=" * 60)
        print("\nPlease check:")
        print("  1. PostgreSQL server is running")
        print("  2. Host and port are correct")
        print("  3. Username and password are correct")
        print("  4. User has permission to create databases")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)

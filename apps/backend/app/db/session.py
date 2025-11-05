"""
Database session configuration.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.db.base import SCHEMA_NAME

# Create sync engine for migrations with schema search path
sync_engine = create_engine(
    settings.get_database_url().replace("+asyncpg", "+psycopg2"),
    pool_pre_ping=True,
    echo=False,
    connect_args={
        "options": f"-c search_path={SCHEMA_NAME},public"
    }
)

# Create async engine for application with schema search path
engine = create_async_engine(
    settings.get_database_url(),
    pool_pre_ping=True,
    echo=False,
    connect_args={
        "server_settings": {
            "search_path": f"{SCHEMA_NAME}, public"
        }
    }
)

# Create sessionmaker for sync operations (migrations)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Create async sessionmaker for application
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency function that yields database sessions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Legacy alias for backward compatibility
async def get_session() -> AsyncSession:
    """Legacy session getter."""
    async for session in get_db():
        yield session
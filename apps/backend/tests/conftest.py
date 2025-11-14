import pytest
import pytest_asyncio
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from sqlalchemy import text

import os
os.environ.setdefault("AUTH_DISABLED", "true")
from app.main import app
from app.db.base import Base, SCHEMA_NAME as MODEL_SCHEMA
from app.db.session import get_db
from app.core.config import settings
from pathlib import Path

# Ensure PostgreSQL-specific types like JSONB compile on SQLite during tests
try:
    from sqlalchemy.dialects.postgresql import JSONB, ARRAY  # type: ignore
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy import types

    @compiles(JSONB, "sqlite")  # type: ignore
    def _jsonb_sqlite(type_, compiler, **kw):  # pragma: no cover - compile-time hook
        # Store as TEXT in SQLite tests
        return "TEXT"

    @compiles(ARRAY, "sqlite")  # type: ignore
    def _array_sqlite(type_, compiler, **kw):  # pragma: no cover - compile-time hook
        # Store ARRAY as TEXT (JSON-encoded) in SQLite tests
        return "TEXT"
except Exception:
    pass


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session using the environment DATABASE_URL.

    - Prefer TESTING_DB_SCHEMA if provided, otherwise DB_SCHEMA.
    - If SQLite is used, translate the schema to default.
    - If Postgres (asyncpg) is used, ensure the schema exists and set search_path.
    - If the configured DB is unreachable, fall back to a local SQLite file.
    """
    db_url = settings.get_database_url()
    # Prefer isolated testing schema when configured, else fall back to model schema
    schema_name = (settings.TESTING_DB_SCHEMA or getattr(Base.metadata, "schema", None) or MODEL_SCHEMA or "public")
    is_sqlite = db_url.startswith("sqlite")

    execution_options = {}
    connect_args = {}
    # Map model schema -> testing schema when using Postgres to keep production schema untouched
    model_schema = (getattr(Base.metadata, "schema", None) or MODEL_SCHEMA or "public")
    use_schema_translate = (not is_sqlite) and (schema_name and schema_name != model_schema)
    if is_sqlite:
        execution_options = {"schema_translate_map": {schema_name: None}}
    elif use_schema_translate:
        execution_options = {"schema_translate_map": {model_schema: schema_name}}
    else:
        # asyncpg: set search_path for tests and a short connect timeout
        connect_args = {
            "server_settings": {"search_path": f"{schema_name}, public"},
            # Allow more time for remote/forwarded DBs to accept connections
            "timeout": 10.0,
        }

    engine = create_async_engine(
        db_url,
        echo=False,
        execution_options=execution_options,
        connect_args=connect_args,
    )

    # Attempt to connect; optionally allow fallback to SQLite only if explicitly enabled
    try:
        async with engine.begin() as conn:
            if not is_sqlite:
                # Ensure schema exists in Postgres and set search_path for this connection
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                await conn.execute(text(f"SET search_path TO {schema_name}, public"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        allow_fallback = os.getenv("ALLOW_SQLITE_FALLBACK", "").lower() in {"1", "true", "yes"}
        if not allow_fallback:
            # Do not hide configuration issues: surface error instead of silently switching DBs
            raise
        await engine.dispose()
        # Fallback to SQLite file under repo-level testing/databases (explicit opt-in)
        repo_root = Path(__file__).resolve().parents[3]
        testing_dir = repo_root / "testing" / "databases"
        testing_dir.mkdir(parents=True, exist_ok=True)
        db_file = testing_dir / "test.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
        is_sqlite = True
        execution_options = {"schema_translate_map": {schema_name: None}}
        connect_args = {}
        engine = create_async_engine(
            db_url,
            echo=False,
            execution_options=execution_options,
            connect_args=connect_args,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,  # avoid attribute refresh IO (MissingGreenlet) in tests
    )

    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        if not is_sqlite and use_schema_translate:
            # Drop entire testing schema to avoid FK cycles on drop_all
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        else:
            await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async test client with a test database."""
    def get_test_db():
        yield db_session
    
    app.dependency_overrides[get_db] = get_test_db
    
    # Support httpx versions that removed the `app` parameter by using ASGITransport
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
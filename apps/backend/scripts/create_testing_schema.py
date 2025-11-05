from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base, SCHEMA_NAME as MODEL_SCHEMA
import asyncio

try:
    from app.core.config import settings
except Exception as e:
    raise SystemExit(f"Failed to import app settings. Ensure PYTHONPATH is set to apps/backend root. Error: {e}")


def main() -> int:
    url = settings.get_database_url()
    url_obj = make_url(url)

    backend = url_obj.get_backend_name()
    if backend.startswith("sqlite"):
        print("SQLite database URL detected; no schema creation needed.")
        return 0

    schema = (getattr(settings, "TESTING_DB_SCHEMA", None) or getattr(settings, "DB_SCHEMA", None) or "public")

    # Avoid printing credentials
    safe_url = url_obj._replace(password="***")
    print(f"Connecting to: {safe_url}")
    print(f"Ensuring schema exists: {schema}")

    # Use async engine when asyncpg is used; otherwise fall back to sync engine
    try:
        if "+asyncpg" in str(safe_url):
            async def run_async():
                engine = create_async_engine(
                    url,
                    pool_pre_ping=True,
                    execution_options={"schema_translate_map": {MODEL_SCHEMA: schema}},
                )
                async with engine.begin() as conn:
                    await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                    # Create all tables for the testing schema using schema translation
                    await conn.run_sync(Base.metadata.create_all)
                await engine.dispose()

            asyncio.run(run_async())
        else:
            engine = create_engine(
                url,
                pool_pre_ping=True,
                execution_options={"schema_translate_map": {MODEL_SCHEMA: schema}},
            )
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                Base.metadata.create_all(bind=conn)
        print(f"Schema ensured: {schema}")
        return 0
    except Exception as e:
        print(f"Error creating schema '{schema}': {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

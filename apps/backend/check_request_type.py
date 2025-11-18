"""Check request type in database."""
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.get_database_url().replace("+asyncpg", "+psycopg2"))

request_id = "e7aabd90-0055-4c81-af13-f8f8f20aae58"

with engine.connect() as conn:
    result = conn.execute(
        text("""
            SELECT id, alias, type, status, project_id
            FROM synthetic_data.requests
            WHERE id = :request_id
        """),
        {"request_id": request_id}
    )
    row = result.fetchone()
    if row:
        print(f"ID: {row[0]}")
        print(f"Alias: {row[1]}")
        print(f"Type: '{row[2]}' (repr: {repr(row[2])})")
        print(f"Status: {row[3]}")
        print(f"Project ID: {row[4]}")
    else:
        print(f"Request {request_id} not found")

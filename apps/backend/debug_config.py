"""
Debug database URL construction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings

print("=" * 60)
print("Database Configuration Debug")
print("=" * 60)

print(f"\nEnvironment Variables:")
print(f"  POSTGRES_SERVER:   {settings.POSTGRES_SERVER}")
print(f"  POSTGRES_PORT:     {settings.POSTGRES_PORT}")
print(f"  POSTGRES_USER:     {settings.POSTGRES_USER}")
print(f"  POSTGRES_DB:       {settings.POSTGRES_DB}")
print(f"  POSTGRES_PASSWORD: {'*' * len(settings.POSTGRES_PASSWORD)}")

print(f"\nConstructed Database URL:")
db_url = settings.get_database_url()
# Mask password in output
masked_url = db_url.replace(settings.POSTGRES_PASSWORD, "***PASSWORD***")
print(f"  {masked_url}")

print(f"\nURL Components:")
parts = db_url.split("://")[1] if "://" in db_url else db_url
print(f"  Protocol: postgresql+asyncpg")
print(f"  User: {settings.POSTGRES_USER}")
print(f"  Host: {settings.POSTGRES_SERVER}")
print(f"  Port: {settings.POSTGRES_PORT}")
print(f"  Database path: /{settings.POSTGRES_DB}")
print(f"  Full database path in URL: {parts.split('@')[1] if '@' in parts else 'N/A'}")

"""
Base SQLAlchemy declarative base and metadata.
"""
import os
from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

# Define the schema for all tables (configurable via env)
SCHEMA_NAME = settings.DB_SCHEMA
# When running under pytest and a TESTING_DB_SCHEMA is provided, prefer it
if os.getenv("PYTEST_CURRENT_TEST") and getattr(settings, "TESTING_DB_SCHEMA", None):
	SCHEMA_NAME = settings.TESTING_DB_SCHEMA  # type: ignore[assignment]

# Create metadata with schema
metadata = MetaData(schema=SCHEMA_NAME)

# Create declarative base with the metadata
Base = declarative_base(metadata=metadata)
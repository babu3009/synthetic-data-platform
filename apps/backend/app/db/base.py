"""
Base SQLAlchemy declarative base and metadata.
"""
import os
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base
from app.core.config import settings

"""Global SQLAlchemy Base and metadata with dynamic schema selection.

Priority order for schema resolution:
1. USE_TESTING_SCHEMA=true and TESTING_DB_SCHEMA set -> testing schema
2. Pytest context (PYTEST_CURRENT_TEST) and TESTING_DB_SCHEMA set -> testing schema
3. Fallback to DB_SCHEMA

This allows switching a developer session to the testing schema without
needing to invoke pytest, while keeping legacy behavior intact.
"""

# Define the schema for all tables (configurable via env)
SCHEMA_NAME = settings.DB_SCHEMA

# Explicit override via USE_TESTING_SCHEMA
if getattr(settings, "USE_TESTING_SCHEMA", False) and getattr(settings, "TESTING_DB_SCHEMA", None):
	SCHEMA_NAME = settings.TESTING_DB_SCHEMA  # type: ignore[assignment]
elif os.getenv("PYTEST_CURRENT_TEST") and getattr(settings, "TESTING_DB_SCHEMA", None):
	SCHEMA_NAME = settings.TESTING_DB_SCHEMA  # type: ignore[assignment]

# Create metadata with schema
metadata = MetaData(schema=SCHEMA_NAME)

# Create declarative base with the metadata
Base = declarative_base(metadata=metadata)
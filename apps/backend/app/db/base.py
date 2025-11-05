"""
Base SQLAlchemy declarative base and metadata.
"""
from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

# Define the schema for all tables
SCHEMA_NAME = "synthetic_data"

# Create metadata with schema
metadata = MetaData(schema=SCHEMA_NAME)

# Create declarative base with the metadata
Base = declarative_base(metadata=metadata)
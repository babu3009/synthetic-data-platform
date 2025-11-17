"""
Entity wizard configuration models for persistent storage.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME


class WizardEntity(Base):
    """Wizard entity configuration for synthetic data generation."""
    __tablename__ = "wizard_entities"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    
    # Entity schema: tables, columns, relationships, layout
    schema_json = Column(JSONB, nullable=False)
    # schema_json structure:
    # {
    #   "tables": [{
    #     "name": str,
    #     "columns": [{
    #       "name": str,
    #       "dtype": str,
    #       "nullable": bool,
    #       "provider": str?,
    #       "providerConfig": dict?,
    #       "pii": bool?,
    #       "piiSubtype": str?,
    #       "regex": str?,
    #       "distribution": str?
    #     }],
    #     "pk": [str]?,
    #     "uniques": [[str]]?,
    #     "rowTarget": {type, value/table/ratio}?
    #   }],
    #   "relationships": [{
    #     "id": str,
    #     "sourceTable": str,
    #     "sourceColumn": str,
    #     "targetTable": str,
    #     "targetColumn": str,
    #     "cardinality": str
    #   }]?,
    #   "layout": {tableName: {x: float, y: float}}?
    # }
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")

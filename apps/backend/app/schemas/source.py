"""
Source Pydantic schemas.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import SourceKind


class SourceBase(BaseModel):
    """Base source schema."""
    kind: SourceKind = Field(..., description="Source data kind")
    storage_uri: str = Field(..., min_length=1, max_length=2048, description="Storage URI")
    checksum: Optional[str] = Field(None, max_length=64, description="SHA-256 checksum")


class SourceCreate(SourceBase):
    """Schema for creating a source."""
    pass


class SourceUpdate(BaseModel):
    """Schema for updating a source."""
    kind: Optional[SourceKind] = None
    storage_uri: Optional[str] = Field(None, min_length=1, max_length=2048)
    checksum: Optional[str] = Field(None, max_length=64)


class SourceInDBBase(SourceBase):
    """Base schema for source in database."""
    id: UUID
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Source(SourceInDBBase):
    """Source schema for API responses."""
    pass


class SourceInDB(SourceInDBBase):
    """Source schema for internal use."""
    pass
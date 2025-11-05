"""
Artifact Pydantic schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import ArtifactFormat


class ArtifactBase(BaseModel):
    """Base artifact schema."""
    format: ArtifactFormat = Field(..., description="Artifact file format")
    storage_uri: str = Field(..., min_length=1, max_length=2048, description="Storage URI")
    size_bytes: int = Field(default=0, ge=0, description="File size in bytes")


class ArtifactCreate(ArtifactBase):
    """Schema for creating an artifact."""
    pass


class ArtifactUpdate(BaseModel):
    """Schema for updating an artifact."""
    storage_uri: str = Field(None, min_length=1, max_length=2048)
    size_bytes: int = Field(None, ge=0)


class ArtifactInDBBase(ArtifactBase):
    """Base schema for artifact in database."""
    id: UUID
    request_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Artifact(ArtifactInDBBase):
    """Artifact schema for API responses."""
    pass


class ArtifactInDB(ArtifactInDBBase):
    """Artifact schema for internal use."""
    pass
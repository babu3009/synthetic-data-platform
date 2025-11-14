"""
Project Pydantic schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(default=None, max_length=1000, description="Project description")
    # Deprecated: backend infers owner from authenticated user; kept optional for compatibility
    owner: Optional[str] = Field(default=None, description="Deprecated: owner email")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    webhook_run_status_url: Optional[str] = Field(
        default=None, max_length=2048, description="Webhook URL for run-status callbacks"
    )
    artifact_ttl_days: Optional[int] = Field(
        default=None, ge=0, description="Artifact retention TTL in days"
    )


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None
    webhook_run_status_url: Optional[str] = Field(default=None, max_length=2048)
    artifact_ttl_days: Optional[int] = Field(default=None, ge=0)


class ProjectInDBBase(ProjectBase):
    """Base schema for project in database."""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Project(ProjectInDBBase):
    """Project schema for API responses."""
    pass


class ProjectInDB(ProjectInDBBase):
    """Project schema for internal use."""
    pass
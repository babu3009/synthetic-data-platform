"""
Project Pydantic schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    owner: str = Field(..., min_length=1, max_length=255, description="Project owner")
    tags: List[str] = Field(default_factory=list, description="Project tags")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    owner: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[List[str]] = None


class ProjectInDBBase(ProjectBase):
    """Base schema for project in database."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Project(ProjectInDBBase):
    """Project schema for API responses."""
    pass


class ProjectInDB(ProjectInDBBase):
    """Project schema for internal use."""
    pass
"""Security/RBAC schemas and enums."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.db.models import ProjectRole


class ProjectMemberBase(BaseModel):
    user_sub: str = Field(..., min_length=1, max_length=255)
    role: ProjectRole


class ProjectMemberCreate(ProjectMemberBase):
    pass


class ProjectMemberUpdate(BaseModel):
    role: Optional[ProjectRole] = None


class ProjectMemberInDBBase(ProjectMemberBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProjectMember(ProjectMemberInDBBase):
    pass

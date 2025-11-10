"""Admin module schema re-exports (Phase 2).

Expose lightweight Pydantic response models for admin user moderation
without altering existing endpoint response shapes. Keeping them here
allows future expansion (e.g., audit events listing) while maintaining
backwards compatibility.
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field

class AdminUser(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    organization: str | None = Field(None, description="Organization")
    status: str = Field(..., description="Current status")

class AdminUserListResponse(BaseModel):
    users: List[AdminUser] = Field(default_factory=list, description="Users matching filter")

__all__ = ["AdminUser", "AdminUserListResponse"]

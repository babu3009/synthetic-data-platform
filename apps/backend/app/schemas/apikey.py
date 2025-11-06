"""Schemas for API key operations."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: List[str] = Field(default_factory=list)


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    scopes: Optional[List[str]] = None


class ApiKeyInDBBase(ApiKeyBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyOut(ApiKeyInDBBase):
    # Only returned on creation
    plaintext_key: Optional[str] = None


class ApiKeyInDB(ApiKeyInDBBase):
    hashed_key: str

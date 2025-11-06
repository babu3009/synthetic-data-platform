"""
Request Pydantic schemas.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.db.models import RequestType, RequestStatus


class RequestBase(BaseModel):
    """Base request schema."""
    type: RequestType = Field(..., description="Type of synthetic data request")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    params_json: Optional[Dict[str, Any]] = Field(None, description="Request parameters as JSON")


class RequestCreate(RequestBase):
    """Schema for creating a request."""
    pass


class RequestUpdate(BaseModel):
    """Schema for updating a request."""
    status: Optional[RequestStatus] = None
    seed: Optional[int] = None
    params_json: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RequestInDBBase(RequestBase):
    """Base schema for request in database."""
    id: UUID
    project_id: UUID
    status: RequestStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class Request(RequestInDBBase):
    """Request schema for API responses."""
    pass


class RequestInDB(RequestInDBBase):
    """Request schema for internal use."""
    pass
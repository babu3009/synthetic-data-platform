"""
LLM-related Pydantic schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic import ValidationError
from pydantic import model_validator
from pydantic.config import ConfigDict


class LLMProviderKind(str):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    CUSTOM = "custom"


# Providers
class LLMProviderBase(BaseModel):
    kind: str = Field(..., description="Provider kind, e.g., openai/anthropic/ollama/lmstudio/custom")
    name: str = Field(..., min_length=1, max_length=255)
    base_url: Optional[str] = Field(None, max_length=1024)
    is_enabled: bool = Field(default=True)


class LLMProviderCreate(LLMProviderBase):
    pass


class LLMProviderUpdate(BaseModel):
    kind: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = Field(None, max_length=1024)
    is_enabled: Optional[bool] = None


class LLMProviderInDBBase(LLMProviderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMProvider(LLMProviderInDBBase):
    pass


# Credentials
class LLMCredentialUpsert(BaseModel):
    api_key: str = Field(..., min_length=1, description="Provider API key (plaintext; will be encrypted at rest)")
    org_id: Optional[str] = Field(default=None, description="Optional organization/account identifier")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific extra fields")


class LLMCredentialOut(BaseModel):
    id: UUID
    provider_id: UUID
    created_at: datetime
    masked_api_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Models
class LLMModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    context_tokens: Optional[int] = None
    supports_json: bool = False
    is_default: bool = False
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class LLMModelCreate(LLMModelBase):
    pass


class LLMModelOut(LLMModelBase):
    id: UUID
    provider_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Project settings
class ProjectLLMSettingBase(BaseModel):
    enabled: bool = False
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    guardrails_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_model_provider_combo(self):
        # If a model_id is provided, a provider_id must also be provided
        if getattr(self, "model_id", None) and not getattr(self, "provider_id", None):
            raise ValueError("model_id requires provider_id to be set")
        return self


class ProjectLLMSettingUpdate(ProjectLLMSettingBase):
    pass


class ProjectLLMSettingOut(ProjectLLMSettingBase):
    id: Optional[UUID] = None
    project_id: UUID
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Operational responses
class ProbeResponse(BaseModel):
    ok: bool
    message: str


class DiscoverModelsResponse(BaseModel):
    models: List[LLMModelOut] = Field(default_factory=list)
    added_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0

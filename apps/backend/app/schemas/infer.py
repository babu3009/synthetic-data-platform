from __future__ import annotations

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class InferColumn(BaseModel):
    table: str = Field(..., description="Table name")
    column: str = Field(..., description="Column name")
    dtype: Optional[str] = Field(None, description="Normalized data type")
    description: Optional[str] = Field(None, description="Free-text description")


class LLMRequest(BaseModel):
    enabled: bool = Field(default=False)
    provider: Optional[str] = Field(default=None, description="openai|anthropic|ollama|lmstudio")
    model: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None)


class InferProvidersRequest(BaseModel):
    columns: List[InferColumn] = Field(default_factory=list)
    llm: Optional[LLMRequest] = Field(default=None)


class Suggestion(BaseModel):
    table: str
    column: str
    provider: Optional[str] = None
    providerConfig: Any
    confidence: float
    rank: int
    reasons: Optional[List[str]] = None
    pii: Optional[dict] = None


class InferProvidersResponse(BaseModel):
    suggestions: List[Suggestion] = Field(default_factory=list)

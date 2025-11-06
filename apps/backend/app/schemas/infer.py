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


class ProviderSuggestion(BaseModel):
    provider_config: Any
    score: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(..., description="'heuristic' or 'LLM'")
    provider: Optional[str] = None
    reasons: Optional[List[str]] = None
    pii: Optional[dict] = None


class ColumnProviderSuggestions(BaseModel):
    table: str
    column: str
    suggestions: List[ProviderSuggestion] = Field(default_factory=list)


class InferProvidersResponse(BaseModel):
    results: List[ColumnProviderSuggestions] = Field(default_factory=list)

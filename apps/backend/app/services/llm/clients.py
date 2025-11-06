from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx


Columns = List[Dict[str, Any]]  # [{name, dtype, description?}]


@dataclass
class SuggestResult:
    provider: str
    model: Optional[str]
    rank: float
    confidence: float
    raw: Optional[Dict[str, Any]] = None


class BaseLLMClient:
    name: str

    def __init__(self, *, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    async def probe(self) -> Tuple[bool, str]:
        """Connectivity probe. Returns (ok, message)."""
        raise NotImplementedError

    async def suggest_providers(
        self,
        *,
        columns: Columns,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> SuggestResult:
        """Common interface returning ranking/confidence for provider/model suggestion."""
        raise NotImplementedError


class OpenAIClient(BaseLLMClient):
    name = "openai"

    async def probe(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "missing api_key"
        url = (self.base_url or "https://api.openai.com/v1").rstrip("/") + "/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code < 500:
                return resp.status_code == 200, f"status={resp.status_code}"
            return False, f"http {resp.status_code}"
        except Exception as e:  # pragma: no cover (network error path)
            return False, str(e)

    async def suggest_providers(
        self,
        *,
        columns: Columns,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> SuggestResult:
        # Heuristic for now: ensure probe works, provide a simple score based on column richness
        ok, _ = await self.probe()
        richness = sum(1 + (1 if c.get("description") else 0) for c in columns)
        rank = 0.6 + min(richness, 10) / 50.0
        confidence = 0.5 + (0.2 if ok else 0.0)
        return SuggestResult(provider=self.name, model=model or self.model, rank=rank, confidence=min(confidence, 0.95))


class AnthropicClient(BaseLLMClient):
    name = "anthropic"

    async def probe(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "missing api_key"
        url = (self.base_url or "https://api.anthropic.com").rstrip("/") + "/v1/models"
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code < 500:
                return resp.status_code in (200, 401, 403), f"status={resp.status_code}"
            return False, f"http {resp.status_code}"
        except Exception as e:  # pragma: no cover
            return False, str(e)

    async def suggest_providers(
        self,
        *,
        columns: Columns,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> SuggestResult:
        ok, _ = await self.probe()
        richness = sum(1 + (1 if c.get("description") else 0) for c in columns)
        rank = 0.58 + min(richness, 10) / 55.0
        confidence = 0.5 + (0.25 if ok else 0.05)
        return SuggestResult(provider=self.name, model=model or self.model, rank=rank, confidence=min(confidence, 0.97))


class OllamaClient(BaseLLMClient):
    name = "ollama"

    async def probe(self) -> Tuple[bool, str]:
        url = (self.base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
            return resp.status_code == 200, f"status={resp.status_code}"
        except Exception as e:  # pragma: no cover
            return False, str(e)

    async def suggest_providers(
        self,
        *,
        columns: Columns,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> SuggestResult:
        ok, _ = await self.probe()
        # Local inference preferred when available
        richness = sum(1 for _ in columns)
        rank = 0.55 + min(richness, 10) / 60.0 + (0.1 if ok else 0.0)
        confidence = 0.45 + (0.25 if ok else 0.05)
        return SuggestResult(provider=self.name, model=model or self.model, rank=min(rank, 0.95), confidence=min(confidence, 0.9))


class LMStudioClient(BaseLLMClient):
    name = "lmstudio"

    async def probe(self) -> Tuple[bool, str]:
        # LM Studio server default port is often 1234
        url = (self.base_url or "http://localhost:1234").rstrip("/") + "/v1/models"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
            return resp.status_code == 200, f"status={resp.status_code}"
        except Exception as e:  # pragma: no cover
            return False, str(e)

    async def suggest_providers(
        self,
        *,
        columns: Columns,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> SuggestResult:
        ok, _ = await self.probe()
        richness = sum(1 for _ in columns)
        rank = 0.54 + min(richness, 10) / 65.0 + (0.08 if ok else 0.0)
        confidence = 0.45 + (0.22 if ok else 0.05)
        return SuggestResult(provider=self.name, model=model or self.model, rank=min(rank, 0.93), confidence=min(confidence, 0.88))

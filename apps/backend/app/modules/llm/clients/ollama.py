from __future__ import annotations

from typing import Optional
import httpx

from .base import BaseLLMClient, SuggestResult, Columns


class OllamaClient(BaseLLMClient):
    name = "ollama"

    async def probe(self):  # type: ignore[override]
        url = (self.base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
            return resp.status_code == 200, f"status={resp.status_code}"
        except Exception as e:  # pragma: no cover
            return False, str(e)

    async def suggest_providers(  # type: ignore[override]
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
        rank = 0.55 + min(richness, 10) / 60.0 + (0.1 if ok else 0.0)
        confidence = 0.45 + (0.25 if ok else 0.05)
        return SuggestResult(provider=self.name, model=model or self.model, rank=min(rank, 0.95), confidence=min(confidence, 0.9))

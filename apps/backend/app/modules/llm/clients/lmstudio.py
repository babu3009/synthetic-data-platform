from __future__ import annotations

from typing import Optional
import httpx

from .base import BaseLLMClient, SuggestResult, Columns


class LMStudioClient(BaseLLMClient):
    name = "lmstudio"

    async def probe(self):  # type: ignore[override]
        url = (self.base_url or "http://localhost:1234").rstrip("/") + "/v1/models"
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
        rank = 0.54 + min(richness, 10) / 65.0 + (0.08 if ok else 0.0)
        confidence = 0.45 + (0.22 if ok else 0.05)
        return SuggestResult(provider=self.name, model=model or self.model, rank=min(rank, 0.93), confidence=min(confidence, 0.88))

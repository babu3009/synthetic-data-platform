from __future__ import annotations

from typing import Optional
import httpx

from .base import BaseLLMClient, SuggestResult, Columns


class OpenAIClient(BaseLLMClient):
    name = "openai"

    async def probe(self):  # type: ignore[override]
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
        richness = sum(1 + (1 if c.get("description") else 0) for c in columns)
        rank = 0.6 + min(richness, 10) / 50.0
        confidence = 0.5 + (0.2 if ok else 0.0)
        return SuggestResult(provider=self.name, model=model or self.model, rank=rank, confidence=min(confidence, 0.95))

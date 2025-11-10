from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


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

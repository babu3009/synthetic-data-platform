from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


def post_run_status(webhook_url: Optional[str], payload: Dict[str, Any]) -> None:
    """Post a minimal run-status payload to the given webhook URL.

    Swallows all errors to avoid impacting the worker path.
    """
    if not webhook_url:
        return
    try:
        httpx.post(webhook_url, json=payload, timeout=5.0)
    except Exception:
        # Ignore webhook errors
        return

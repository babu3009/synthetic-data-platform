from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def test_validate_endpoint(async_client: AsyncClient):
    payload = {
        "rules": [
            {"when": "orders.total > 1000", "then": ["orders.channel in ['WEB','PARTNER']"]},
            {"uniqueness": ["orders.id"]},
            {"distribution": {"product.category": {"A": 0.5, "B": 0.3, "C": 0.2}}},
            {"temporal": "shipment.promised_date <= shipment.order_date + 2d"},
        ],
        "data_sample": {
            "orders": [
                {"id": 1, "total": 1500, "channel": "WEB"},
                {"id": 2, "total": 500, "channel": "STORE"},
            ],
            "product": [{"category": "A"}] * 5 + [{"category": "B"}] * 3 + [{"category": "C"}] * 2,
            "shipment": [
                {"promised_date": "2024-01-03T00:00:00", "order_date": "2024-01-01T00:00:00"}
            ],
        },
        "data_final": {
            "orders": [
                {"id": 3, "total": 2000, "channel": "PARTNER"},
                {"id": 3, "total": 1200, "channel": "STORE"},
            ],
            "product": [{"category": "A"}] * 8 + [{"category": "B"}] * 1 + [{"category": "C"}] * 1,
            "shipment": [
                {"promised_date": "2024-01-05T00:00:00", "order_date": "2024-01-01T00:00:00"}
            ],
        },
        "max_violations": 5,
    }
    resp = await async_client.post("/api/v1/validate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "rules" in body and isinstance(body["rules"], list)
    assert "report" in body and {"sample", "final"}.issubset(body["report"].keys())

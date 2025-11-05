from __future__ import annotations

from app.services.rules_dsl import parse_rules


def test_parse_rules_basic():
    dsl = {
        "rules": [
            {"when": "orders.total > 1000", "then": ["orders.channel in ['WEB','PARTNER']"]},
            {"uniqueness": ["customers.email"]},
            {"distribution": {"product.category": {"A": 0.5, "B": 0.3, "C": 0.2}}},
            {"temporal": "shipment.promised_date <= shipment.order_date + 2d"},
        ]
    }
    rules = parse_rules(dsl)
    kinds = [r["type"] for r in rules]
    assert kinds == ["implication", "uniqueness", "distribution", "temporal"]
    # implication table inferred as 'orders'
    assert rules[0]["table"] == "orders"
    # uniqueness normalization
    assert rules[1] == {"type": "uniqueness", "table": "customers", "columns": ["email"]}
    # distribution normalization
    assert rules[2]["type"] == "distribution" and rules[2]["column"] == "category"
    # temporal normalization
    assert rules[3]["type"] == "temporal" and rules[3]["right"]["offset_days"] == 2

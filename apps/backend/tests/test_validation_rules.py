from __future__ import annotations

from app.services.rules_dsl import parse_rules
from app.services.validator import validate_rules


def test_implication_and_uniqueness_validation():
    dsl = {
        "rules": [
            {"when": "orders.total > 1000", "then": ["orders.channel in ['WEB','PARTNER']"]},
            {"uniqueness": ["orders.id"]},
        ]
    }
    rules = parse_rules(dsl)

    rows = [
        {"id": 1, "total": 1500, "channel": "WEB"},
        {"id": 2, "total": 500, "channel": "STORE"},
        {"id": 3, "total": 2000, "channel": "PARTNER"},
        {"id": 3, "total": 1200, "channel": "STORE"},  # dup id and violation of implication
    ]
    data = {"orders": rows}
    report = validate_rules(rules, data, data, max_violations=5)

    imp = report["sample"][0]
    uniq = report["sample"][1]
    # implication: two rows checked (totals > 1000), one violation (channel STORE)
    assert imp["checked"] == 3  # totals > 1000 on rows 0,2,3
    assert imp["violations"] == 1
    # uniqueness: duplicate id should be flagged
    assert uniq["violations"] == 1

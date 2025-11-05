from __future__ import annotations

from app.services.validator import validate_rules


def test_distribution_chi2_pass_and_fail():
    rules = [
        {"type": "distribution", "table": "product", "column": "category", "probs": {"A": 0.5, "B": 0.3, "C": 0.2}},
    ]
    # Sample dataset roughly matches the distribution
    data_ok = {
        "product": (
            [{"category": "A"}] * 50
            + [{"category": "B"}] * 30
            + [{"category": "C"}] * 20
        )
    }
    # Final dataset skewed heavily
    data_bad = {
        "product": (
            [{"category": "A"}] * 80
            + [{"category": "B"}] * 10
            + [{"category": "C"}] * 10
        )
    }

    report = validate_rules(rules, data_ok, data_bad)
    sample_stat = report["sample"][0]["stat"]
    final_stat = report["final"][0]["stat"]
    assert sample_stat["pass"] is True
    assert final_stat["pass"] is False

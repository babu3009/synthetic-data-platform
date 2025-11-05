from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple
from datetime import datetime, timedelta

from .rules_dsl import evaluate_expression


def _collect_rows(dataset: Dict[str, List[Dict[str, Any]]], table: str) -> List[Dict[str, Any]]:
    return dataset.get(table, [])


_CHI2_CRITICAL_95 = {
    # df: critical value at alpha=0.05 (95th percentile)
    1: 3.841,
    2: 5.991,
    3: 7.815,
    4: 9.488,
    5: 11.070,
    6: 12.592,
    7: 14.067,
    8: 15.507,
    9: 16.919,
    10: 18.307,
}


def _chi2_test(observed: Dict[str, int], expected_probs: Dict[str, float]) -> Dict[str, Any]:
    n = sum(observed.values())
    if n == 0:
        return {"n": 0, "chi2": 0.0, "df": max(len(expected_probs) - 1, 1), "pass": True}
    chi2 = 0.0
    cats = expected_probs.keys()
    for c in cats:
        exp = expected_probs.get(c, 0.0) * n
        obs = observed.get(c, 0)
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp
    df = max(len([p for p in expected_probs.values() if p > 0]) - 1, 1)
    crit = _CHI2_CRITICAL_95.get(df, 18.307)  # fallback df>=10
    return {"n": n, "chi2": chi2, "df": df, "critical": crit, "pass": chi2 <= crit}


def _first_n(lst: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    return lst[:n]


def validate_rules(rules: List[Dict[str, Any]], data_sample: Dict[str, List[Dict[str, Any]]], data_final: Dict[str, List[Dict[str, Any]]], max_violations: int = 10) -> Dict[str, Any]:
    report: Dict[str, Any] = {"sample": [], "final": []}

    def eval_on(dataset: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for r in rules:
            rtype = r.get("type")
            table = r.get("table", "")
            rows = _collect_rows(dataset, table)
            res: Dict[str, Any] = {"type": rtype, "table": table}
            if rtype == "implication":
                when = r["when"]
                thens = r["then"]
                checked = 0
                violations: List[Dict[str, Any]] = []
                for idx, row in enumerate(rows):
                    try:
                        if evaluate_expression(when, row, table):
                            checked += 1
                            for cond in thens:
                                if not evaluate_expression(cond, row, table):
                                    if len(violations) < max_violations:
                                        violations.append({"row": idx, "row_data": row, "failed": cond})
                                    break
                    except Exception as e:  # pragma: no cover
                        if len(violations) < max_violations:
                            violations.append({"row": idx, "error": str(e)})
                res.update({
                    "checked": checked,
                    "violations": len(violations),
                    "violation_rate": (len(violations) / checked) if checked else 0.0,
                    "samples": _first_n(violations, max_violations),
                })
            elif rtype == "uniqueness":
                cols = r["columns"]
                key = cols[0]
                seen = set()
                dups = []
                for idx, row in enumerate(rows):
                    v = row.get(key)
                    if v in seen:
                        if len(dups) < max_violations:
                            dups.append({"row": idx, key: v})
                    else:
                        seen.add(v)
                res.update({
                    "checked": len(rows),
                    "violations": len(dups),
                    "violation_rate": (len(dups) / len(rows)) if rows else 0.0,
                    "samples": _first_n(dups, max_violations),
                })
            elif rtype == "distribution":
                col = r["column"]
                probs: Dict[str, float] = r["probs"]
                counts: Dict[str, int] = Counter([str(row.get(col)) for row in rows])  # type: ignore[arg-type]
                stat = _chi2_test(counts, probs)
                res.update({"checked": sum(counts.values()), "stat": stat, "observed": dict(counts)})
            elif rtype == "temporal":
                # Only same-table comparisons are supported; evaluates lhs <= rhs_column + offset_days
                left = r["left"]
                op = r["op"]
                right = r["right"]
                rcol = right["column"]
                offset_days = int(right.get("offset_days", 0))
                checked = 0
                violations: List[Dict[str, Any]] = []
                for idx, row in enumerate(rows):
                    lhs_val = _resolve_field(left, row)
                    rhs_val = _resolve_field(rcol, row)
                    if lhs_val is None or rhs_val is None:
                        continue
                    try:
                        lhs_dt = _to_datetime(lhs_val)
                        rhs_dt = _to_datetime(rhs_val) + timedelta(days=offset_days)
                        ok = _compare_dates(lhs_dt, rhs_dt, op)
                        checked += 1
                        if not ok and len(violations) < max_violations:
                            violations.append({"row": idx, "lhs": str(lhs_dt), "rhs": str(rhs_dt)})
                    except Exception as e:  # pragma: no cover
                        if len(violations) < max_violations:
                            violations.append({"row": idx, "error": str(e)})
                res.update({
                    "checked": checked,
                    "violations": len(violations),
                    "violation_rate": (len(violations) / checked) if checked else 0.0,
                    "samples": _first_n(violations, max_violations),
                })
            else:
                res.update({"error": "unknown rule type"})
            results.append(res)
        return results

    report["sample"] = eval_on(data_sample)
    report["final"] = eval_on(data_final)
    return report


def _resolve_field(ref: str, row: Dict[str, Any]) -> Any:
    # supports 'table.column' or 'column'
    if "." in ref:
        _, c = ref.split(".", 1)
    else:
        c = ref
    return row.get(c)


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # try common ISO forms
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass
    raise ValueError("Unsupported datetime value")


def _compare_dates(a: datetime, b: datetime, op: str) -> bool:
    if op == "<=":
        return a <= b
    if op == ">=":
        return a >= b
    if op == "<":
        return a < b
    if op == ">":
        return a > b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    raise ValueError("Unsupported comparator")

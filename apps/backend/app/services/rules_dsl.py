from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union
import ast


# Supported expression evaluator (safe subset)
ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.IfExp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Subscript,
    ast.Index,
    ast.Slice,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
)


def _safe_eval(expr: str, context: Dict[str, Any]) -> Any:
    """Evaluate a simple boolean/value expression safely with a provided context.
    Context exposes both 'column' and 'table.column' forms if provided.
    """
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Unsupported expression node: {type(node).__name__}")
    return eval(compile(tree, filename="<expr>", mode="eval"), {"__builtins__": {}}, context)


def _normalize_ref(ref: str) -> Tuple[str, str]:
    """Split 'table.column' into (table, column). If no dot, table is empty string."""
    if "." in ref:
        t, c = ref.split(".", 1)
        return t, c
    return "", ref


def parse_rules(dsl: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse the rules DSL into a normalized JSON list of rules."""
    rules_in = dsl.get("rules", [])
    out: List[Dict[str, Any]] = []
    for item in rules_in:
        if "when" in item and "then" in item:
            # Implication rule; infer table from first identifier with a dot or from 'when'
            when = item["when"]
            thens = item["then"]
            # best-effort table detection: prefer explicit table prefix in when; else in first then
            table = ""
            for token in [when] + list(thens):
                if isinstance(token, str) and "." in token:
                    table = token.split(".", 1)[0]
                    break
            out.append({
                "type": "implication",
                "table": table,
                "when": when,
                "then": list(thens),
            })
        elif "uniqueness" in item:
            cols: List[str] = item["uniqueness"]
            for ref in cols:
                t, c = _normalize_ref(ref)
                out.append({"type": "uniqueness", "table": t, "columns": [c]})
        elif "distribution" in item:
            dist: Dict[str, Dict[str, float]] = item["distribution"]
            for ref, probs in dist.items():
                t, c = _normalize_ref(ref)
                out.append({
                    "type": "distribution",
                    "table": t,
                    "column": c,
                    "probs": probs,
                })
        elif "temporal" in item:
            expr = item["temporal"]
            # parse pattern like "shipment.promised_date <= order.order_date + 2d"
            # We'll normalize as {type: temporal, table, left: str, op: str, right: {column: str, offset_days: int}}
            # Simplified parser:
            parts = None
            for op in ["<=", ">=", "<", ">", "==", "!="]:
                if op in expr:
                    lhs, rhs = [p.strip() for p in expr.split(op, 1)]
                    parts = (lhs, op, rhs)
                    break
            if not parts:
                raise ValueError("Unsupported temporal rule; missing comparator")
            lhs, op, rhs = parts
            # rhs may be like "order.order_date + 2d" or just a column
            offset_days = 0
            if "+" in rhs:
                rcol, offset = [p.strip() for p in rhs.split("+", 1)]
                if offset.endswith("d"):
                    offset_days = int(offset[:-1])
                rhs_col = rcol
            else:
                rhs_col = rhs
            table, _ = _normalize_ref(lhs)
            out.append({
                "type": "temporal",
                "table": table,
                "left": lhs,
                "op": op,
                "right": {"column": rhs_col, "offset_days": offset_days},
            })
        else:
            raise ValueError("Unknown rule item")
    return out


def evaluate_expression(expr: str, row: Dict[str, Any], table: str = "") -> bool:
    """Evaluate an expression on a single row.
    Provides both column and table.column names in the context.
    """
    ctx = dict(row)
    # also add table-prefixed names if table provided
    if table:
        for k, v in row.items():
            ctx[f"{table}.{k}"] = v
    return bool(_safe_eval(expr, ctx))

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


# --- Public interface ---


@dataclass
class ColumnSpec:
    table: str
    column: str
    dtype: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LLMConfig:
    enabled: bool = False
    provider: Optional[str] = None  # openai|anthropic|ollama|lmstudio
    model: Optional[str] = None
    temperature: Optional[float] = None


def infer_providers(
    columns: Iterable[ColumnSpec],
    *,
    llm: Optional[LLMConfig] = None,
) -> List[Dict[str, Any]]:
    """Return ranked provider suggestions for given columns.

    Each suggestion item:
      { table, column, provider, providerConfig, confidence, rank, reasons?, pii? }
    """
    # 1) Heuristic baseline
    base_suggestions: List[Dict[str, Any]] = []
    for col in columns:
        sug = _heuristic_suggest(col)
        if sug:
            base_suggestions.append(sug)

    # 2) Optional LLM refinement
    if llm and llm.enabled and _llm_available(llm):
        try:
            refined = _llm_refine(columns, base_suggestions, llm)
            if refined:
                base_suggestions = refined
        except Exception:
            # Best-effort only
            pass

    # Rank by confidence descending; stable by table/column
    base_suggestions.sort(key=lambda s: (-(s.get("confidence") or 0.0), s.get("table",""), s.get("column","")))
    for i, s in enumerate(base_suggestions, start=1):
        s["rank"] = i
    return base_suggestions


def infer_providers_combined(
    columns: Iterable[ColumnSpec],
    *,
    llm_enabled: bool = False,
    llm_provider: Optional[str] = None,
    temperature: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return per-column suggestions combining heuristic and (optional) LLM-refined scores.

    Output shape:
      [{
        "table": str,
        "column": str,
        "suggestions": [
          {"provider_config": Any, "score": float, "source": "heuristic"|"LLM", "provider": Optional[str], "reasons": [str]?, "pii": dict?}
        ]
      }]
    """
    # Build heuristic suggestions first (one per column at most)
    base = []
    for col in columns:
        s = _heuristic_suggest(col)
        if s:
            base.append(s)

    # Optionally run the LLM refine path to adjust confidences
    refined = None
    if llm_enabled:
        refined = _llm_refine(columns, list(base), LLMConfig(enabled=True, provider=llm_provider, temperature=temperature)) or base

    # Index by (table,column)
    by_col: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for s in base:
        key = (s["table"], s["column"])
        by_col[key] = s

    results: List[Dict[str, Any]] = []
    for (table, column), hs in by_col.items():
        suggestions: List[Dict[str, Any]] = []
        # Heuristic entry
        suggestions.append({
            "provider_config": hs.get("providerConfig"),
            "score": float(hs.get("confidence") or 0.0),
            "source": "heuristic",
            "provider": hs.get("provider"),
            "reasons": hs.get("reasons"),
            **({"pii": hs.get("pii")} if hs.get("pii") else {}),
        })
        # LLM entry if available
        if refined is not None:
            rs = next((r for r in refined if r["table"] == table and r["column"] == column), None)
            if rs:
                suggestions.append({
                    "provider_config": rs.get("providerConfig"),
                    "score": float(rs.get("confidence") or 0.0),
                    "source": "LLM",
                    "provider": rs.get("provider"),
                    "reasons": rs.get("reasons"),
                    **({"pii": rs.get("pii")} if rs.get("pii") else {}),
                })
        # Rank suggestions by score first; for equal scores, prefer LLM over heuristic
        def sort_key(it: Dict[str, Any]):
            return (float(it.get("score") or 0.0), 1 if it.get("source") == "LLM" else 0)

        suggestions.sort(key=sort_key, reverse=True)
        results.append({"table": table, "column": column, "suggestions": suggestions})

    # Preserve input order as best effort
    order = [(c.table, c.column) for c in columns]
    order_idx = {k: i for i, k in enumerate(order)}
    results.sort(key=lambda r: order_idx.get((r["table"], r["column"]), 10**9))
    return results


# --- Heuristics ---


_EMAIL_PAT = re.compile(r"\bemail\b|e[-_ ]?mail", re.I)
_PHONE_PAT = re.compile(r"\b(phone|mobile|cell|tel|telephone)\b", re.I)
_NAME_FIRST_PAT = re.compile(r"\b(first[_-]?name|fname)\b", re.I)
_NAME_LAST_PAT = re.compile(r"\b(last[_-]?name|lname|surname|family[_-]?name)\b", re.I)
_NAME_FULL_PAT = re.compile(r"\b(full[_-]?name|name)\b", re.I)
_ADDRESS_PAT = re.compile(r"\b(address|street|addr)\b", re.I)
_CITY_PAT = re.compile(r"\bcity\b", re.I)
_STATE_PAT = re.compile(r"\bstate|province|region\b", re.I)
_ZIP_PAT = re.compile(r"\b(zip|postal|postcode)\b", re.I)
_COUNTRY_PAT = re.compile(r"\bcountry\b", re.I)
_UUID_PAT = re.compile(r"\b(uuid|guid)\b", re.I)
_ID_PAT = re.compile(r"\b(id|identifier)\b", re.I)
_IBAN_PAT = re.compile(r"\biban\b", re.I)
_CARD_PAT = re.compile(r"\b(card|credit)\b", re.I)
_IP_PAT = re.compile(r"\b(ip|ipv4|ipv6)\b", re.I)
_URL_PAT = re.compile(r"\b(url|uri|website|link)\b", re.I)
_DATE_PAT = re.compile(r"\b(date|timestamp|datetime|created_at|updated_at)\b", re.I)
_AMOUNT_PAT = re.compile(r"\b(amount|price|total|cost|balance|revenue|salary|payment)\b", re.I)


def _text(s: Optional[str]) -> str:
    return (s or "").strip()


def _heuristic_suggest(col: ColumnSpec) -> Optional[Dict[str, Any]]:
    name = f"{col.table}.{col.column}".lower()
    colname = col.column.lower()
    dtype = _text(col.dtype).lower()
    desc = _text(col.description).lower()
    hay = " ".join([name, colname, dtype, desc])

    reasons: List[str] = []
    provider: Optional[str] = None
    provider_cfg: Any = None
    pii: Optional[Dict[str, Any]] = None
    confidence = 0.5

    def set_cfg(cfg: Any, prov: Optional[str] = None, conf: float = 0.8, reason: Optional[str] = None, pii_tag: Optional[str] = None):
        nonlocal provider_cfg, provider, confidence, pii
        provider_cfg = cfg
        provider = prov
        confidence = conf
        if reason:
            reasons.append(reason)
        if pii_tag:
            pii = {"tag": pii_tag}

    # PII and common tokens
    if _EMAIL_PAT.search(hay):
        set_cfg("email", prov="email", conf=0.98, reason="column looks like email", pii_tag="contact.email")
    elif _PHONE_PAT.search(hay):
        set_cfg("phone", prov="phone", conf=0.9, reason="column looks like phone", pii_tag="contact.phone")
    elif _NAME_FIRST_PAT.search(hay):
        set_cfg("first_name", prov="first_name", conf=0.9, reason="first name detected", pii_tag="person.first_name")
    elif _NAME_LAST_PAT.search(hay):
        set_cfg("last_name", prov="last_name", conf=0.9, reason="last name detected", pii_tag="person.last_name")
    elif _NAME_FULL_PAT.search(hay):
        set_cfg("name", prov="name", conf=0.75, reason="name-like column", pii_tag="person.name")
    elif _ADDRESS_PAT.search(hay):
        set_cfg("address", prov="address", conf=0.75, reason="address-like column", pii_tag="location.address")
    elif _CITY_PAT.search(hay):
        set_cfg("city", prov="city", conf=0.7, reason="city token" )
    elif _STATE_PAT.search(hay):
        set_cfg("state", prov="state", conf=0.7, reason="state/province token")
    elif _ZIP_PAT.search(hay):
        set_cfg("postal_code", prov="postal_code", conf=0.7, reason="postal/zip token")
    elif _COUNTRY_PAT.search(hay):
        set_cfg("country", prov="country", conf=0.7, reason="country token")
    elif _UUID_PAT.search(hay):
        set_cfg({"type": "uuid4"}, prov="uuid4", conf=0.85, reason="uuid token")
    elif _ID_PAT.search(hay) and ("int" in dtype or dtype in {"bigint", "integer", "number"}):
        set_cfg({"type": "sequence", "start": 1}, prov="sequence", conf=0.75, reason="id integer implies sequence")
    elif _IBAN_PAT.search(hay):
        # Not exact, but a checksum provider is a reasonable starting point
        set_cfg({"type": "checksum", "length": 22}, prov="iban-like", conf=0.6, reason="iban token (use checksum)" )
    elif _CARD_PAT.search(hay):
        set_cfg({"type": "checksum", "length": 16}, prov="luhn", conf=0.65, reason="card token (luhn-like)" )
    elif _IP_PAT.search(hay):
        set_cfg("ipv4", prov="ipv4", conf=0.7, reason="ip token")
    elif _URL_PAT.search(hay):
        set_cfg("url", prov="url", conf=0.7, reason="url token")
    elif _DATE_PAT.search(hay) or ("date" in dtype or "time" in dtype):
        set_cfg({"type": "date_range", "start": "2018-01-01", "end": "2025-01-01"}, prov="date_range", conf=0.8, reason="date-like column")
    elif _AMOUNT_PAT.search(hay) or ("decimal" in dtype or "numeric" in dtype or "float" in dtype):
        # Use log-normal for positive skew amounts
        set_cfg({"type": "expression", "expression": "round(abs(rng.lognormvariate(3,1)),2)"}, prov="lognormal", conf=0.7, reason="amount-like numeric")

    if provider_cfg is None:
        return None

    return {
        "table": col.table,
        "column": col.column,
        "provider": provider,
        "providerConfig": provider_cfg,
        "confidence": confidence,
        "reasons": reasons,
        **({"pii": pii} if pii else {}),
    }


# --- Optional LLM plug-in (best-effort, only if configured) ---


def _llm_available(cfg: LLMConfig) -> bool:
    prov = (cfg.provider or "").lower()
    if not prov:
        return False
    if prov == "openai" and os.getenv("OPENAI_API_KEY"):
        return True
    if prov == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return True
    if prov in {"ollama", "lmstudio"}:
        # Local endpoints; assume available if enabled
        return True
    return False


def _llm_refine(
    columns: Iterable[ColumnSpec],
    suggestions: List[Dict[str, Any]],
    cfg: LLMConfig,
) -> Optional[List[Dict[str, Any]]]:
    # For now, keep it simple: use the LLM to adjust confidence for ambiguous columns only.
    # No hard dependency on provider SDKs.
    # If something goes wrong, return None and keep baseline.
    ambig = [s for s in suggestions if (s.get("confidence") or 0.0) < 0.75]
    if not ambig:
        return suggestions
    try:
        # Placeholder: in a real implementation, call provider and nudge confidences
        for s in ambig:
            s["confidence"] = min(0.85, (s.get("confidence") or 0.5) + 0.1)
            rs = s.get("reasons") or []
            rs.append(f"llm:{cfg.provider or 'auto'} nudged")
            s["reasons"] = rs
        return suggestions
    except Exception:
        return None

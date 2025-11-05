from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from .base import BaseProvider, Context
from .providers import (
    SequenceProvider,
    PatternProvider,
    CategoricalProvider,
    DateRangeProvider,
    ExpressionProvider,
    GeoBoxProvider,
    ChecksumProvider,
    ReferenceProvider,
    EmpiricalProvider,
)

try:
    from .providers import FakerProvider  # type: ignore
except Exception:  # pragma: no cover
    FakerProvider = None  # type: ignore


# PII catalog maps to provider configurations
PII_CATALOG: Dict[str, Dict[str, Any]] = {
    "email": {"type": "faker", "method": "email"},
    "phone": {"type": "faker", "method": "phone_number"},
    "address": {"type": "faker", "method": "address"},
    "name": {"type": "faker", "method": "name"},
    "dob": {"type": "date_range", "start": "1950-01-01", "end": "2010-12-31"},
    "national_id": {"type": "checksum", "length": 12},
    "credit_card": {"type": "faker", "method": "credit_card_number"},
    "iban": {"type": "faker", "method": "iban"},
    "ip": {"type": "faker", "method": "ipv4"},
    "device_id": {"type": "pattern", "pattern": "????????-????????"},
}


class ProviderRegistry:
    @staticmethod
    def from_config(config: Any) -> Callable[[int, Context], Any]:
        """Create a callable generator from config.

        Config can be a dict or JSON string. If config is a string key found in PII_CATALOG, that mapping is used.
        The returned callable expects (n, context) and returns a list of samples.
        """
        if isinstance(config, str):
            # allow PII catalog shorthand or JSON string
            if config in PII_CATALOG:
                cfg = PII_CATALOG[config]
            else:
                cfg = json.loads(config)
        elif isinstance(config, dict):
            cfg = config
        else:
            raise TypeError("config must be dict, str key, or JSON string")

        ptype = cfg.get("type")
        unique = bool(cfg.get("unique", False))

        def build_provider() -> BaseProvider:
            if ptype == "sequence":
                return SequenceProvider(start=cfg.get("start", 0), step=cfg.get("step", 1), template=cfg.get("template"), unique=unique)
            if ptype == "pattern":
                return PatternProvider(pattern=cfg["pattern"], unique=unique)
            if ptype == "categorical":
                return CategoricalProvider(categories=cfg["categories"], weights=cfg.get("weights"), unique=unique)
            if ptype == "date_range":
                return DateRangeProvider(start=cfg["start"], end=cfg["end"], fmt=cfg.get("format", "%Y-%m-%d"), unique=unique)
            if ptype == "expression":
                return ExpressionProvider(expression=cfg["expression"], unique=unique)
            if ptype == "geobox":
                return GeoBoxProvider(min_lat=cfg["min_lat"], max_lat=cfg["max_lat"], min_lon=cfg["min_lon"], max_lon=cfg["max_lon"], as_dict=cfg.get("as_dict", False), unique=unique)
            if ptype == "checksum":
                return ChecksumProvider(length=cfg.get("length", 16), prefix=cfg.get("prefix", ""), unique=unique)
            if ptype == "reference":
                return ReferenceProvider(key=cfg["key"], unique=unique)
            if ptype == "empirical":
                return EmpiricalProvider(csv_path=cfg["csv"], column=cfg.get("column"), unique=unique)
            if ptype == "faker":
                if FakerProvider is None:
                    raise RuntimeError("Faker is not installed, cannot use faker provider")
                return FakerProvider(method=cfg["method"], locale=cfg.get("locale"), unique=unique)
            # Allow shorthand like {pii: "email"}
            if "pii" in cfg:
                return ProviderRegistry.from_config(PII_CATALOG[cfg["pii"]])  # type: ignore
            raise ValueError(f"Unknown provider type: {ptype}")

        provider = build_provider()

        def generator(n: int, context: Context):
            return list(provider.sample(n, context))

        return generator

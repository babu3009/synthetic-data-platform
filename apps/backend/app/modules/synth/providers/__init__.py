"""Re-exports for synth providers under the modules namespace (Phase 3).

This adapter keeps provider imports stable while we gradually move to
module-oriented structure. All real implementations remain under
`apps/backend/synth/providers/*`.
"""

from synth.providers.registry import ProviderRegistry as ProviderRegistry  # noqa: F401
from synth.providers.base import BaseProvider as BaseProvider, Context as Context  # noqa: F401
from synth.providers import providers as _providers  # noqa: F401

# Expose commonly used provider classes for convenience
from synth.providers.providers import (  # noqa: F401
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

try:  # optional faker provider
    from synth.providers.providers import FakerProvider as FakerProvider  # type: ignore # noqa: F401
except Exception:  # pragma: no cover
    FakerProvider = None  # type: ignore

__all__ = [
    "ProviderRegistry",
    "BaseProvider",
    "Context",
    "SequenceProvider",
    "PatternProvider",
    "CategoricalProvider",
    "DateRangeProvider",
    "ExpressionProvider",
    "GeoBoxProvider",
    "ChecksumProvider",
    "ReferenceProvider",
    "EmpiricalProvider",
    "FakerProvider",
]

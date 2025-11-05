from __future__ import annotations

from typing import Protocol, Iterable, Any, Dict, Optional, List, Union, runtime_checkable
import hashlib
import random

Context = Dict[str, Any]


def _hash_seed(*parts: Union[str, int]) -> int:
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"|")
    # reduce to 64-bit for Python's Random
    return int.from_bytes(h.digest()[:8], "big", signed=False)


def make_rng(context: Context) -> random.Random:
    """Create a deterministic RNG from context.

    Uses seed = hash(global_seed, table, column).
    """
    global_seed = context.get("global_seed", 0)
    table = context.get("table", "")
    column = context.get("column", "")
    return random.Random(_hash_seed(global_seed, table, column))


@runtime_checkable
class BaseProvider(Protocol):
    def sample(self, n: int, context: Context) -> Iterable[Any]:
        ...


class UniqueMixin:
    """Mixin to enforce uniqueness when requested.

    Providers can set self.unique = True in config to request unique outputs.
    If uniqueness cannot be satisfied after reasonable attempts, raises ValueError.
    """

    unique: bool = False

    def _enforce_unique(self, values: Iterable[Any], max_attempts: int, generator, context: Context) -> List[Any]:
        if not self.unique:
            return list(values)
        seen = set()
        out: List[Any] = []
        attempts = 0
        for v in values:
            if v not in seen:
                seen.add(v)
                out.append(v)
            else:
                # try to regenerate until unique or attempts exceeded
                while attempts < max_attempts:
                    attempts += 1
                    nv = generator(context)
                    if nv not in seen:
                        seen.add(nv)
                        out.append(nv)
                        break
                else:
                    raise ValueError("Unable to satisfy uniqueness constraint; increase domain size or disable unique=True")
        return out

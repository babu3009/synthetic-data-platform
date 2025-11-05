from __future__ import annotations

import ast
import csv
import math
from types import SimpleNamespace
import os
from datetime import datetime, timedelta, date
from typing import Any, Dict, Iterable, List, Optional

from .base import BaseProvider, Context, make_rng, UniqueMixin


class SequenceProvider(UniqueMixin):
    def __init__(self, start: int = 0, step: int = 1, template: Optional[str] = None, unique: bool = False):
        self.start = start
        self.step = step
        self.template = template
        self.unique = unique

    def _one(self, i: int) -> Any:
        val = self.start + i * self.step
        if self.template:
            return self.template.format(i=i, value=val)
        return val

    def sample(self, n: int, context: Context) -> Iterable[Any]:
        vals = [self._one(i) for i in range(n)]
        # sequence is naturally unique if step!=0; still apply UniqueMixin to be safe
        return self._enforce_unique(vals, max_attempts=n * 2, generator=lambda ctx: self._one(len(vals)), context=context)


class PatternProvider(UniqueMixin):
    """Generates strings from a simple pattern.

    Supported tokens:
    - '#': random digit 0-9
    - 'A': random uppercase letter A-Z
    - 'a': random lowercase letter a-z
    - '?': random alphanumeric [A-Za-z0-9]
    Other characters are copied verbatim.
    """

    def __init__(self, pattern: str, unique: bool = False):
        self.pattern = pattern
        self.unique = unique

    def _one(self, rng) -> str:
        out = []
        for ch in self.pattern:
            if ch == '#':
                out.append(str(rng.randint(0, 9)))
            elif ch == 'A':
                out.append(chr(rng.randint(ord('A'), ord('Z'))))
            elif ch == 'a':
                out.append(chr(rng.randint(ord('a'), ord('z'))))
            elif ch == '?':
                r = rng.randint(0, 61)
                if r < 10:
                    out.append(str(r))
                elif r < 36:
                    out.append(chr(ord('A') + r - 10))
                else:
                    out.append(chr(ord('a') + r - 36))
            else:
                out.append(ch)
        return ''.join(out)

    def sample(self, n: int, context: Context) -> Iterable[str]:
        rng = make_rng(context)
        def gen(_):
            return self._one(rng)
        vals = [gen(context) for _ in range(n)]
        return self._enforce_unique(vals, max_attempts=n * 10, generator=gen, context=context)


class CategoricalProvider(UniqueMixin):
    def __init__(self, categories: List[Any], weights: Optional[List[float]] = None, unique: bool = False):
        if not categories:
            raise ValueError("categories must be non-empty")
        self.categories = categories
        self.weights = weights
        self.unique = unique

    def sample(self, n: int, context: Context) -> Iterable[Any]:
        rng = make_rng(context)
        if self.unique:
            if n > len(set(self.categories)):
                raise ValueError("Requested unique samples exceed number of unique categories")
            # sample without replacement deterministically
            pool = list(dict.fromkeys(self.categories))  # preserve order, unique
            rng.shuffle(pool)
            return pool[:n]
        if self.weights:
            # normalized weighted sampling
            total = sum(self.weights)
            w = [x / total for x in self.weights]
            # precompute cumulative
            cum = []
            s = 0.0
            for x in w:
                s += x
                cum.append(s)
            def draw_one():
                r = rng.random()
                for idx, c in enumerate(cum):
                    if r <= c:
                        return self.categories[idx]
                return self.categories[-1]
            return [draw_one() for _ in range(n)]
        else:
            return [rng.choice(self.categories) for _ in range(n)]


class DateRangeProvider(UniqueMixin):
    def __init__(self, start: str, end: str, fmt: str = "%Y-%m-%d", unique: bool = False):
        self.start_date = datetime.strptime(start, fmt).date()
        self.end_date = datetime.strptime(end, fmt).date()
        if self.end_date < self.start_date:
            raise ValueError("end < start")
        self.fmt = fmt
        self.unique = unique

    def sample(self, n: int, context: Context) -> Iterable[str]:
        rng = make_rng(context)
        days = (self.end_date - self.start_date).days + 1
        if self.unique:
            if n > days:
                raise ValueError("Requested unique dates exceed range")
            idxs = list(range(days))
            rng.shuffle(idxs)
            picks = idxs[:n]
        else:
            picks = [rng.randrange(days) for _ in range(n)]
        return [(self.start_date + timedelta(days=i)).strftime(self.fmt) for i in picks]


class ExpressionProvider(UniqueMixin):
    """Evaluates a safe Python expression per row.

    Allowed nodes: literals, Name, BinOp, BoolOp, Compare, IfExp, Call (whitelisted funcs), UnaryOp, Subscript on lists/tuples, Attribute on math module.
    Available names: rng (Random), i (row index), math (module subset), context (dict)
    """

    ALLOWED_FUNCS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'int': int,
        'float': float,
        'str': str,
        'len': len,
    }

    ALLOWED_MATH = {k: getattr(math, k) for k in (
        'sqrt','sin','cos','tan','log','log10','exp','ceil','floor','fabs','pow','pi','e'
    )}

    ALLOWED_NODES = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
        ast.Name, ast.Load, ast.Call, ast.Constant, ast.Subscript, ast.Tuple, ast.List,
        ast.Dict, ast.Attribute, ast.Index, ast.Slice,
        # operators and comparators
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Not,
        ast.And, ast.Or,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE
    )

    ALLOWED_RNG_METHODS = {"random", "randint", "randrange", "uniform", "choice"}

    def __init__(self, expression: str, unique: bool = False):
        self.expression = expression
        self.unique = unique
        self._ast = ast.parse(expression, mode='eval')
        # validate AST
        for node in ast.walk(self._ast):
            if not isinstance(node, self.ALLOWED_NODES):
                raise ValueError(f"Disallowed AST node: {type(node).__name__}")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'math':
                        # ensure attribute is an allowed math symbol
                        if not (isinstance(node.func.attr, str) and node.func.attr in self.ALLOWED_MATH):
                            raise ValueError("math attribute not allowed")
                    elif isinstance(node.func.value, ast.Name) and node.func.value.id == 'rng':
                        # allow a safe subset of rng methods
                        if not (isinstance(node.func.attr, str) and node.func.attr in self.ALLOWED_RNG_METHODS):
                            raise ValueError("Only whitelisted rng methods allowed: random, randint, randrange, uniform, choice")
                    else:
                        raise ValueError("Only math.* or rng.* calls allowed via attribute")
                elif isinstance(node.func, ast.Name):
                    if node.func.id not in self.ALLOWED_FUNCS:
                        raise ValueError(f"Function {node.func.id} not allowed")

    def _eval_one(self, rng, i, context: Context):
        env = {**self.ALLOWED_FUNCS, 'math': SimpleNamespace(**self.ALLOWED_MATH), 'rng': rng, 'i': i, 'context': context}
        return eval(compile(self._ast, '<expr>', 'eval'), {"__builtins__": {}}, env)

    def sample(self, n: int, context: Context) -> Iterable[Any]:
        rng = make_rng(context)
        vals = [self._eval_one(rng, i, context) for i in range(n)]
        def gen(ctx):
            j = len(vals)
            return self._eval_one(rng, j, ctx)
        return self._enforce_unique(vals, max_attempts=n * 5, generator=gen, context=context)


class GeoBoxProvider(UniqueMixin):
    def __init__(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float, as_dict: bool = False, unique: bool = False):
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90 and -180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("Invalid lat/lon bounds")
        if max_lat < min_lat or max_lon < min_lon:
            raise ValueError("max < min for lat/lon")
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.as_dict = as_dict
        self.unique = unique

    def sample(self, n: int, context: Context) -> Iterable[Any]:
        rng = make_rng(context)
        def gen_one():
            lat = rng.uniform(self.min_lat, self.max_lat)
            lon = rng.uniform(self.min_lon, self.max_lon)
            if self.as_dict:
                return {"lat": lat, "lon": lon}
            return (lat, lon)
        vals = [gen_one() for _ in range(n)]
        return self._enforce_unique(vals, max_attempts=n * 10, generator=lambda ctx: gen_one(), context=context)


class ChecksumProvider(UniqueMixin):
    """Luhn checksum number generator.

    Config: length (total digits), prefix (string of digits)
    """

    def __init__(self, length: int = 16, prefix: str = "", unique: bool = False):
        if length <= 1:
            raise ValueError("length must be > 1")
        if prefix and not prefix.isdigit():
            raise ValueError("prefix must be digits")
        if len(prefix) >= length:
            raise ValueError("prefix length must be < length")
        self.length = length
        self.prefix = prefix
        self.unique = unique

    @staticmethod
    def _luhn_checksum(number: str) -> int:
        digits = [int(d) for d in number]
        s = 0
        parity = (len(digits) + 1) % 2
        for i, d in enumerate(digits):
            if i % 2 == parity:
                d *= 2
                if d > 9:
                    d -= 9
            s += d
        return (10 - (s % 10)) % 10

    def _one(self, rng) -> str:
        body_len = self.length - len(self.prefix) - 1
        body = ''.join(str(rng.randint(0, 9)) for _ in range(body_len))
        partial = f"{self.prefix}{body}"
        check = self._luhn_checksum(partial)
        return f"{partial}{check}"

    def sample(self, n: int, context: Context) -> Iterable[str]:
        rng = make_rng(context)
        vals = [self._one(rng) for _ in range(n)]
        return self._enforce_unique(vals, max_attempts=n * 20, generator=lambda ctx: self._one(rng), context=context)


class ReferenceProvider(UniqueMixin):
    def __init__(self, key: str, unique: bool = False):
        self.key = key
        self.unique = unique

    def sample(self, n: int, context: Context) -> Iterable[Any]:
        pool = context.get('key_pool', {}).get(self.key)
        if pool is None:
            raise KeyError(f"key_pool missing key '{self.key}'")
        rng = make_rng(context)
        if self.unique:
            if n > len(pool):
                raise ValueError("Requested unique references exceed pool size")
            idxs = list(range(len(pool)))
            rng.shuffle(idxs)
            return [pool[i] for i in idxs[:n]]
        else:
            return [pool[rng.randrange(len(pool))] for _ in range(n)]


class EmpiricalProvider(UniqueMixin):
    def __init__(self, csv_path: str, column: Optional[str] = None, unique: bool = False):
        self.csv_path = csv_path
        self.column = column
        self.unique = unique
        self._data: Optional[List[Any]] = None

    def _load(self) -> List[Any]:
        if self._data is not None:
            return self._data
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(self.csv_path)
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f) if self.column else csv.reader(f)
            if self.column:
                self._data = [row[self.column] for row in reader if self.column in row]
            else:
                self._data = [row[0] for row in reader]
        if not self._data:
            raise ValueError("CSV contains no data")
        return self._data

    def sample(self, n: int, context: Context) -> Iterable[Any]:
        data = self._load()
        rng = make_rng(context)
        if self.unique:
            if n > len(data):
                raise ValueError("Requested unique empirical samples exceed dataset size")
            idxs = list(range(len(data)))
            rng.shuffle(idxs)
            return [data[i] for i in idxs[:n]]
        else:
            return [data[rng.randrange(len(data))] for _ in range(n)]


# Optional Faker provider
try:
    from faker import Faker

    class FakerProvider(UniqueMixin):
        def __init__(self, method: str, locale: Optional[str] = None, unique: bool = False):
            self.method = method
            self.locale = locale
            self.unique = unique
            self._fk_cache: dict = {}

        def _get_faker(self, context: Context) -> Faker:
            # faker seeding can be achieved via .seed_instance with a deterministic seed
            fk_key = self.locale or "default"
            fk = self._fk_cache.get(fk_key)
            if fk is None:
                fk = Faker(self.locale)
                self._fk_cache[fk_key] = fk
            # derive deterministic seed per context to make outputs stable
            seed = int(make_rng(context).random() * 2**31)
            fk.seed_instance(seed)
            return fk

        def _one(self, fk: Faker) -> Any:
            prov = getattr(fk, self.method)
            return prov()

        def sample(self, n: int, context: Context) -> Iterable[Any]:
            fk = self._get_faker(context)
            if self.unique:
                fk_unique = fk.unique
                vals = [getattr(fk_unique, self.method)() for _ in range(n)]
                # faker.unique keeps internal registry; clear for next calls with different context
                fk.unique.clear()
                return vals
            else:
                return [self._one(fk) for _ in range(n)]

except Exception:  # pragma: no cover - Faker not installed
    FakerProvider = None  # type: ignore

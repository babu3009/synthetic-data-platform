import os
import tempfile
from synth.providers.registry import ProviderRegistry


def ctx(seed=123, table="t", column="c", key_pool=None):
    return {"global_seed": seed, "table": table, "column": column, "key_pool": key_pool or {}}


def test_determinism_categorical():
    cfg = {"type": "categorical", "categories": ["A", "B", "C"], "weights": [1, 2, 3]}
    gen = ProviderRegistry.from_config(cfg)
    out1 = gen(10, ctx(seed=42, table="t1", column="x"))
    out2 = gen(10, ctx(seed=42, table="t1", column="x"))
    assert out1 == out2
    out3 = gen(10, ctx(seed=42, table="t1", column="y"))
    assert out1 != out3  # different column changes stream


def test_uniqueness_reference_provider():
    pool = {"users": ["u1", "u2", "u3", "u4"]}
    gen = ProviderRegistry.from_config({"type": "reference", "key": "users", "unique": True})
    out = gen(4, ctx(key_pool=pool))
    assert len(out) == 4
    assert len(set(out)) == 4


def test_reference_unique_raises_when_exceeds():
    pool = {"ids": [1, 2]}
    gen = ProviderRegistry.from_config({"type": "reference", "key": "ids", "unique": True})
    try:
        gen(3, ctx(key_pool=pool))
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_date_range_determinism_and_uniqueness():
    gen = ProviderRegistry.from_config({"type": "date_range", "start": "2020-01-01", "end": "2020-01-10", "unique": True})
    a = gen(10, ctx(seed=99))
    b = gen(10, ctx(seed=99))
    assert a == b
    assert len(set(a)) == 10


def test_checksum_luhn():
    gen = ProviderRegistry.from_config({"type": "checksum", "length": 12, "prefix": "42"})
    vals = gen(5, ctx(seed=7))
    assert all(v.startswith("42") and len(v) == 12 for v in vals)


def test_expression_safe_and_deterministic():
    gen = ProviderRegistry.from_config({"type": "expression", "expression": "int(1000 + 10 * i + math.floor(rng.random()*5))"})
    a = gen(5, ctx(seed=5))
    b = gen(5, ctx(seed=5))
    assert a == b


def test_empirical_bootstrap_unique():
    # create a temp csv
    with tempfile.NamedTemporaryFile(mode="w", delete=False, newline="") as f:
        f.write("val\nA\nB\nC\nD\n")
        path = f.name
    try:
        gen = ProviderRegistry.from_config({"type": "empirical", "csv": path, "column": "val", "unique": True})
        vals = gen(4, ctx(seed=11))
        assert len(set(vals)) == 4
    finally:
        os.remove(path)


def test_pii_catalog_shortcuts():
    email_gen = ProviderRegistry.from_config("email")
    out = email_gen(3, ctx(seed=1))
    assert len(out) == 3

from __future__ import annotations

from pathlib import Path

from app.services.flat import preview, generate_to_artifacts


def test_preview_determinism():
    schema = {
        "seed": 123,
        "fields": [
            {"name": "id", "provider": {"type": "sequence", "start": 1}},
            {"name": "color", "provider": {"type": "categorical", "categories": ["red", "green", "blue"]}},
        ],
    }
    r1 = preview(schema)
    r2 = preview(schema)
    assert r1 == r2
    assert len(r1) == 100


def test_generate_to_artifacts_csv(tmp_path: Path):
    schema = {
        "seed": 42,
        "fields": [
            {"name": "id", "provider": {"type": "sequence", "start": 0}},
            {"name": "group", "provider": {"type": "categorical", "categories": ["A", "B", "C"]}},
        ],
    }
    out_paths, stats = generate_to_artifacts(
        target_dir=tmp_path,
        schema=schema,
        total_rows=10_000,
        formats=["csv"],
        chunk_size=2_000,
    )
    assert out_paths, "no output paths returned"
    csv_path = out_paths[0]
    assert csv_path.exists(), "CSV file not created"
    # Rough size check and stats presence
    assert "id" in stats and "group" in stats
    assert stats["id"]["cardinality"] == 10_000

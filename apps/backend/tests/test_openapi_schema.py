from pathlib import Path
import json
from app.main import app


def test_openapi_contains_health_and_metadata(tmp_path):
    schema = app.openapi()
    # basic invariants
    assert '/health' in schema.get('paths', {}), 'health path missing'
    info = schema.get('info', {})
    assert info.get('title'), 'title missing'
    assert info.get('version'), 'version missing'
    # write snapshot-like file for debug if needed
    (tmp_path / 'openapi-sample.json').write_text(json.dumps({'paths': list(schema.get('paths', {}).keys())[:5]}), encoding='utf-8')

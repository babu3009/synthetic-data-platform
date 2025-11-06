import os
import json
import pytest

from app.utils.crypto import encrypt_json, decrypt_json, mask_secret


def test_encrypt_decrypt_roundtrip(monkeypatch):
    # Use a deterministic key for tests
    monkeypatch.setenv("LLM_SECRET_KEY", "test-secret-passphrase-123")

    obj = {"api_key": "sk-abcdef1234567890", "org_id": "org_123", "extra": {"a": 1}}

    cipher = encrypt_json(obj)
    assert isinstance(cipher, str)
    assert cipher != json.dumps(obj, separators=(",", ":"))

    plain = decrypt_json(cipher)
    assert plain == obj


def test_mask_secret():
    assert mask_secret("123456") == "***3456"
    assert mask_secret("abc") == "***abc"
    assert mask_secret("") == ""
    assert mask_secret(None) == ""

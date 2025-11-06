"""
Crypto utilities for encrypting/decrypting JSON payloads for LLM credentials.

- Uses Fernet symmetric encryption by default.
- Reads key from env LLM_SECRET_KEY; if it is not a valid Fernet key, derives one from the value.
- Optionally can fetch a key from Azure Key Vault when KEY_VAULT_URL and KEY_VAULT_SECRET_NAME are provided
  and azure packages are available; otherwise falls back to env key.

Public API:
- encrypt_json(obj) -> str
- decrypt_json(s: str) -> object
- mask_secret(s: str) -> str  # helper to mask secrets (show last 4)
"""
from __future__ import annotations

import base64
import json
import os
import hashlib
from typing import Any, Optional

_FERNET: Optional["Fernet"] = None


def _get_fernet_key_bytes() -> bytes:
    # Try Azure Key Vault if configured and available
    kv_url = os.getenv("KEY_VAULT_URL")
    kv_secret = os.getenv("KEY_VAULT_SECRET_NAME")
    if kv_url and kv_secret:
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore
            from azure.keyvault.secrets import SecretClient  # type: ignore

            cred = DefaultAzureCredential()
            client = SecretClient(vault_url=kv_url, credential=cred)
            secret = client.get_secret(kv_secret)
            value = secret.value or ""
            if not value:
                raise RuntimeError("Empty Key Vault secret value")
            return _coerce_to_fernet_key(value)
        except Exception:
            # Fall back to env-based key if Key Vault not available or fails
            pass

    # Fall back to local env key
    env_key = os.getenv("LLM_SECRET_KEY", "")
    if not env_key:
        raise RuntimeError("LLM_SECRET_KEY not set and Key Vault not configured")
    return _coerce_to_fernet_key(env_key)


def _coerce_to_fernet_key(value: str) -> bytes:
    """Coerce an arbitrary string to a valid Fernet key.

    If the value already looks like a 32-byte urlsafe base64 key, use as-is;
    otherwise derive a stable key via sha256 and encode urlsafe base64.
    """
    try:
        raw = base64.urlsafe_b64decode(value)
        if len(raw) == 32:
            return value.encode("utf-8")
    except Exception:
        pass
    # Derive from arbitrary secret/passphrase
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> "Fernet":
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    try:
        from cryptography.fernet import Fernet  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("cryptography package is required for Fernet encryption") from e
    key = _get_fernet_key_bytes()
    _FERNET = Fernet(key)
    return _FERNET


def encrypt_json(obj: Any) -> str:
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    try:
        f = _get_fernet()
        token = f.encrypt(data)
        return token.decode("utf-8")
    except RuntimeError:
        # Fallback to weak encryption (dev/test only)
        key = _get_fernet_key_bytes()
        cipher = _weak_encrypt(data, key)
        return "weak:" + base64.urlsafe_b64encode(cipher).decode("utf-8")


def decrypt_json(s: str) -> Any:
    if s.startswith("weak:"):
        raw = base64.urlsafe_b64decode(s.split(":", 1)[1])
        key = _get_fernet_key_bytes()
        data = _weak_decrypt(raw, key)
        return json.loads(data.decode("utf-8"))
    try:
        f = _get_fernet()
        data = f.decrypt(s.encode("utf-8"))
        return json.loads(data.decode("utf-8"))
    except RuntimeError:
        # Attempt weak as last resort
        raw = base64.urlsafe_b64decode(s)
        key = _get_fernet_key_bytes()
        data = _weak_decrypt(raw, key)
        return json.loads(data.decode("utf-8"))


def mask_secret(s: Optional[str]) -> str:
    if not s:
        return ""
    # Keep last 4 characters
    tail = s[-4:] if len(s) >= 4 else s
    return "***" + tail


# --- Weak fallback cipher (dev/test only) ---
def _weak_keystream(length: int, key: bytes) -> bytes:
    out = bytearray()
    counter = 0
    seed = key
    while len(out) < length:
        counter_bytes = counter.to_bytes(8, "big")
        block = hashlib.sha256(seed + counter_bytes).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _weak_encrypt(data: bytes, key: bytes) -> bytes:
    ks = _weak_keystream(len(data), key)
    return bytes([a ^ b for a, b in zip(data, ks)])


def _weak_decrypt(data: bytes, key: bytes) -> bytes:
    # XOR is symmetric
    return _weak_encrypt(data, key)

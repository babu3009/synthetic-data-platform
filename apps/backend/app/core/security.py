"""Security shim re-exporting existing JWT/password helpers (Phase 0)."""

from app.security.jwt import create_access_token, decode_token  # re-export
from app.security.passwords import verify_password, get_password_hash  # re-export

__all__ = [
    "create_access_token",
    "decode_token",
    "verify_password",
    "get_password_hash",
]

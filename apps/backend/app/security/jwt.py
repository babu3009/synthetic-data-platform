import time
import jwt
from typing import Any, Dict
from app.core.config import settings

ALGO = "HS256"


def create_access_token(sub: str, role: str, expires_minutes: int = 60) -> str:
    now = int(time.time())
    exp = now + expires_minutes * 60
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, settings.AUTH_JWT_SECRET, algorithm=ALGO)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.AUTH_JWT_SECRET, algorithms=[ALGO])

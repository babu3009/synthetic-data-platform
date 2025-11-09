import hashlib
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.core.config import settings


def _hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def generate_otp_and_hash(user_id: str, purpose: str, ttl_hours: int) -> Tuple[str, str, datetime]:
    # 6-digit numeric
    otp = f"{random.randint(0, 999999):06d}"
    # per-user salt
    salt = os.urandom(16).hex()
    otp_hash = _hash(f"{user_id}:{purpose}:{otp}:{salt}") + ":" + salt
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    return otp, otp_hash, expires_at


def verify_otp(user_id: str, purpose: str, otp: str, otp_hash: str) -> bool:
    try:
        stored_hash, salt = otp_hash.split(":", 1)
    except ValueError:
        return False
    return stored_hash == _hash(f"{user_id}:{purpose}:{otp}:{salt}")

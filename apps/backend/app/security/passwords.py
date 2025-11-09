from passlib.context import CryptContext
from app.core.config import settings

# Try argon2 first, fallback bcrypt
schemes = ["argon2", "bcrypt"]
pwd_context = CryptContext(schemes=schemes, deprecated="auto")

COMMON_BLOCKLIST = {"password", "123456", "qwerty", "letmein", "admin"}

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def validate_password_policy(password: str) -> None:
    if len(password) < settings.PASSWORD_POLICY_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_POLICY_MIN_LENGTH} characters.")
    if password.lower() in COMMON_BLOCKLIST:
        raise ValueError("Password too common.")

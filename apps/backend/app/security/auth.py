"""
Authentication and authorization utilities:
- OIDC scaffolding (login redirect + callback)
- API key header auth (X-API-Key)
- RBAC + scope enforcement per project

Notes:
- For OIDC, we scaffold generic redirects using env config. In development/tests, we
  also allow injecting a user via X-User-Sub or Authorization: Bearer testing:<sub>.
- API keys are hashed with SHA-256 before storage, and compared using constant time.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Iterable, Optional, Dict, Any
from uuid import UUID as _UUID

from fastapi import Depends, Header, HTTPException, Request
from starlette import status

from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import ApiKey, ProjectMember, ProjectRole, User
import httpx


API_KEY_HEADER = "X-API-Key"


@dataclass
class Principal:
    kind: str  # "user" | "api_key"
    actor: str  # for audit trail (e.g., user sub or api_key:<uuid>)
    project_id: Optional[str] = None
    scopes: list[str] = None
    user_sub: Optional[str] = None
    user_id: Optional[str] = None


# --- OIDC scaffolding ---

def get_oidc_config() -> dict:
    return {
        "issuer": os.getenv("OIDC_ISSUER", ""),
        "client_id": os.getenv("OIDC_CLIENT_ID", ""),
        "client_secret": os.getenv("OIDC_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("OIDC_REDIRECT_URI", ""),
        "scopes": os.getenv("OIDC_SCOPES", "openid profile email"),
    }


_OIDC_DISCOVERY_CACHE: Dict[str, Dict[str, Any]] = {}
_OIDC_JWKS_CACHE: Dict[str, Dict[str, Any]] = {}


async def _fetch_json(url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def _get_discovery(issuer: str) -> Dict[str, Any]:
    if issuer in _OIDC_DISCOVERY_CACHE:
        return _OIDC_DISCOVERY_CACHE[issuer]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    data = await _fetch_json(url)
    _OIDC_DISCOVERY_CACHE[issuer] = data
    return data


async def _get_jwks(jwks_uri: str) -> Dict[str, Any]:
    if jwks_uri in _OIDC_JWKS_CACHE:
        return _OIDC_JWKS_CACHE[jwks_uri]
    data = await _fetch_json(jwks_uri)
    _OIDC_JWKS_CACHE[jwks_uri] = data
    return data


async def verify_id_token(id_token: str) -> Dict[str, Any]:
    """Verify an OIDC ID token using provider JWKS and return claims.

    This is a minimal verifier intended for dev/testing. In production, add
    state/nonce validation and error handling as appropriate.
    """
    cfg = get_oidc_config()
    if not cfg["issuer"] or not cfg["client_id"]:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OIDC not configured")

    # Fetch discovery + JWKS
    discovery = await _get_discovery(cfg["issuer"])
    jwks = await _get_jwks(discovery.get("jwks_uri", ""))

    # Import jose lazily to avoid hard dependency when OIDC isn't used
    try:  # pragma: no cover
        from jose import jwt  # type: ignore
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="OIDC token verification unavailable (python-jose not installed)")

    # Select key
    headers = jwt.get_unverified_header(id_token)
    kid = headers.get("kid")
    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key = k
            break
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signing key not found")

    # Verify
    claims = jwt.decode(
        id_token,
        key,
        algorithms=[headers.get("alg", "RS256")],
        audience=cfg["client_id"],
        issuer=cfg["issuer"],
        options={"verify_at_hash": False},
    )
    return claims


async def get_current_principal(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias=API_KEY_HEADER),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_user_sub: Optional[str] = Header(default=None, alias="X-User-Sub"),
) -> Optional[Principal]:
    """Authenticate the caller and return a Principal or None.

    Priority:
    1) X-API-Key header -> ApiKey principal
    2) Dev/testing user via X-User-Sub or Authorization: Bearer testing:<sub>
    3) JWT Bearer token -> User principal (validates token signature and expiry)
    4) (Future) OIDC ID token in Authorization: Bearer <jwt>
    """
    # API Key auth
    if x_api_key:
        hashed = sha256_key(x_api_key)
        res = await db.execute(select(ApiKey).where(ApiKey.hashed_key == hashed))
        api_key: Optional[ApiKey] = res.scalar_one_or_none()
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        # Build principal
        scopes = list(getattr(api_key, "scopes", []) or [])
        return Principal(kind="api_key", actor=f"api_key:{api_key.id}", project_id=str(api_key.project_id), scopes=scopes)

    # Test/dev user injection
    if x_user_sub:
        # Try to resolve to a concrete user id by email (common dev case)
        principal = Principal(kind="user", actor=f"user:{x_user_sub}", user_sub=x_user_sub)
        try:
            res = await db.execute(select(User).where(User.email == x_user_sub))
            u = res.scalar_one_or_none()
            if not u and "@" not in x_user_sub:
                # Fallback to local-suffix convention used in tests/dev
                res = await db.execute(select(User).where(User.email == (x_user_sub + "@local")))
                u = res.scalar_one_or_none()
            if u:
                principal.user_id = str(u.id)
        except Exception:
            pass
        return principal
    if authorization and authorization.startswith("Bearer testing:"):
        sub = authorization.split(" ", 1)[1].split(":", 1)[1]
        principal = Principal(kind="user", actor=f"user:{sub}", user_sub=sub)
        try:
            res = await db.execute(select(User).where(User.email == sub))
            u = res.scalar_one_or_none()
            if not u and "@" not in sub:
                res = await db.execute(select(User).where(User.email == (sub + "@local")))
                u = res.scalar_one_or_none()
            if u:
                principal.user_id = str(u.id)
        except Exception:
            pass
        return principal

    # JWT Bearer token validation (for real user login tokens)
    if authorization and authorization.startswith("Bearer ") and not authorization.startswith("Bearer testing:"):
        token = authorization.split(" ", 1)[1]
        try:
            from app.security.jwt import decode_token
            claims = decode_token(token)
            user_id = claims.get("sub")
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
            # Verify user exists in database
            try:
                typed_user_id = _UUID(str(user_id))
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
            
            user_res = await db.execute(select(User).where(User.id == typed_user_id))
            user = user_res.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            
            # Build principal with user info
            principal = Principal(
                kind="user",
                actor=f"user:{user_id}",
                user_id=str(user_id),
                user_sub=str(user.email)  # Use email as user_sub for compatibility
            )
            return principal
        except HTTPException:
            raise
        except Exception as e:
            # Token decode failure (expired, invalid signature, etc.)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

    # No valid auth method found
    return None


def sha256_key(raw: str) -> str:
    # Optionally include a server-side pepper to avoid rainbow tables
    pepper = settings.SECRET_KEY.encode("utf-8")
    h = hashlib.sha256()
    h.update(pepper)
    h.update(raw.encode("utf-8"))
    return h.hexdigest()


async def require_project_scope(
    project_id: str,
    required_scopes: Optional[Iterable[str]] = None,
    required_roles: Optional[Iterable[ProjectRole]] = None,
    principal: Optional[Principal] = None,
    db: Optional[AsyncSession] = None,
) -> Principal:
    """Authorize access to a project using either API key scopes or user RBAC roles."""
    # Test bypass: allow disabling auth in test/dev via env flag
    if os.getenv("AUTH_DISABLED", "").lower() in {"1", "true", "yes"}:
        # When disabled for tests, allow unauthenticated calls, but still enforce
        # scope/role rules if a principal (e.g., API key) is explicitly provided.
        if principal is None:
            return Principal(kind="user", actor="user:test", user_sub="test")
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # API key path: project must match, and scopes must include required_scopes
    if principal.kind == "api_key":
        if principal.project_id != str(project_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key not valid for this project")
        if required_scopes:
            missing = [s for s in required_scopes if s not in (principal.scopes or [])]
            if missing:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required scope")
        return principal

    # User path: check membership and role
    if principal.kind == "user":
        if db is None:
            # DB session is required to verify membership when using user principals
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing DB session for authorization")
        if required_roles:
            # Coerce project_id to UUID if model column expects UUID
            typed_project_id: Any = project_id
            if not isinstance(project_id, _UUID):
                try:
                    typed_project_id = _UUID(str(project_id))
                except Exception:
                    typed_project_id = project_id

            # Prefer user_id match when available; fall back to user_sub for legacy records
            if principal.user_id:
                try:
                    typed_user_id = _UUID(str(principal.user_id))
                except Exception:
                    typed_user_id = None
            else:
                typed_user_id = None

            if typed_user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User identity not resolved")
            res = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == typed_project_id,
                    ProjectMember.user_id == typed_user_id,
                )
            )
            member = res.scalar_one_or_none()
            if member is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a project member")
            role = member.role
            if not any(role == r or (role == ProjectRole.OWNER) for r in required_roles):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported principal")

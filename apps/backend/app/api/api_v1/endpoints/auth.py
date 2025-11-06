"""OIDC auth scaffolding.

Provides:
- GET /auth/login -> returns provider authorize URL (frontend can redirect)
- GET /auth/callback -> placeholder that would validate state/code and set session

For now, we only echo the configuration pieces to demonstrate wiring.
"""
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException

from app.security.auth import get_oidc_config, verify_id_token

router = APIRouter()


@router.get("/auth/login")
async def login_start() -> dict:
    cfg = get_oidc_config()
    if not cfg["issuer"] or not cfg["client_id"] or not cfg["redirect_uri"]:
        return {"enabled": False, "reason": "Missing OIDC config"}
    # In a real implementation, we'd fetch the provider's authorization_endpoint from
    # the OIDC discovery document. Here we scaffold a generic authorize URL.
    authorize_url = f"{cfg['issuer'].rstrip('/')}/authorize?" + urlencode({
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": cfg.get("scopes", "openid"),
        "state": "todo-state",
        "nonce": "todo-nonce",
    })
    return {"enabled": True, "authorize_url": authorize_url}


@router.get("/auth/callback")
async def login_callback(request: Request) -> dict:
    # Placeholder: in a full implementation, we'd exchange 'code' for tokens.
    # For scaffolding/testing, if an 'id_token' query param is present, verify it.
    params = dict(request.query_params)
    id_token = params.get("id_token")
    if id_token:
        try:
            claims = await verify_id_token(id_token)
            # In a real app, set a session cookie here tying the user to claims["sub"].
            return {"verified": True, "claims": {k: claims.get(k) for k in ("sub", "email", "name") if k in claims}}
        except HTTPException as e:
            raise e
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=401, detail=f"Invalid ID token: {e}")
    return {"received": params, "note": "Provide id_token to verify or implement token exchange"}

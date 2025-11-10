"""Re-export user-related Pydantic schemas for Phase 2 modularization.

We purposely re-export only the response models actually used by the public
`/users/*` endpoints so that moving import paths later (Phase 3+) will not be
breaking for callers that rely on OpenAPI schema component stability.

Notes:
- We currently piggy-back on auth schemas for profile + avatar responses.
- If we later introduce write/update profile endpoints, introduce dedicated
	request models here instead of importing from `auth`.
"""

from app.schemas.auth import UserProfile, AvatarUploadResponse  # re-export shim

__all__ = [
		"UserProfile",
		"AvatarUploadResponse",
]

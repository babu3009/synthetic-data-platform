"""Auth schema re-exports (Phase 2).

We re-export Pydantic models from ``app.schemas.auth`` to provide a stable
module-local import path without moving the original source yet. This keeps
OpenAPI unchanged while allowing gradual adoption:

	from app.modules.auth.schemas import LoginRequest

Later phases may relocate definitions fully; for now we just alias them.
"""

from app.schemas.auth import (
	RegisterRequest,
	RegisterResponse,
	VerifyEmailRequest,
	VerifyEmailResponse,
	LoginRequest,
	LoginResponse,
	ResendEmailOTPRequest,
	ForgotPasswordRequest,
	ResetPasswordRequest,
	ChangePasswordRequest,
	UserProfile,
	AvatarUploadResponse,
)

__all__ = [
	"RegisterRequest",
	"RegisterResponse",
	"VerifyEmailRequest",
	"VerifyEmailResponse",
	"LoginRequest",
	"LoginResponse",
	"ResendEmailOTPRequest",
	"ForgotPasswordRequest",
	"ResetPasswordRequest",
	"ChangePasswordRequest",
	"UserProfile",
	"AvatarUploadResponse",
]


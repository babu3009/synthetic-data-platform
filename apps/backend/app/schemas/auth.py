from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    organization: Optional[str] = None

class RegisterResponse(BaseModel):
    status: str
    message: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)

class VerifyEmailResponse(BaseModel):
    status: str
    message: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str

class ResendEmailOTPRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)

class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = Field(default=None)
    new_password: str = Field(min_length=8)
    otp: Optional[str] = Field(default=None, min_length=6, max_length=6)

class UserProfile(BaseModel):
    id: str
    email: EmailStr
    organization: Optional[str]
    role: str
    status: str
    profile_image_url: Optional[str]
    last_login_at: Optional[datetime]

class AvatarUploadResponse(BaseModel):
    profile_image_url: str
    message: str

import enum
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.app_users.models import AuthProvider


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthRequest(BaseModel):
	email: EmailStr
	provider: AuthProvider = AuthProvider.google
	provider_id: str


class UserResponse(BaseModel):
	id: UUID
	email: EmailStr
	is_admin: bool = False
	created_at: datetime
	updated_at: datetime
	provider: str

	model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
	token: str
	user: UserResponse


class PasswordResetTokenRequest(BaseModel):
	token: str
	expires_at: datetime
	model_config = ConfigDict(from_attributes=True)

class ForgotPasswordRequest(BaseModel):
	email: EmailStr


class ResetPasswordRequest(BaseModel):
	token: str
	new_password: str

class GoogleLoginRequest(BaseModel):
	token: str

class MessageResponse(BaseModel):
	message: str
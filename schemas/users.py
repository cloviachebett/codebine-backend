import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=12)
    role: str = "ANALYST"
    phone: Optional[str] = None


class UserRead(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    role: str
    account_status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    phone: Optional[str] = None
    mfa_enrolled: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    account_status: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str
    mfa_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshPayload(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str

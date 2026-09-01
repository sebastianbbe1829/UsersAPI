from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordRecoveryResponse(BaseModel):
    message: str
    expires_at: datetime | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=6, max_length=200)


class PasswordResetResponse(BaseModel):
    message: str

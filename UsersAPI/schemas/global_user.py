from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GlobalSuperCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class GlobalSuperUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)
    is_active: bool | None = None


class GlobalSuperMfaVerifyRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class GlobalSuperRead(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    mfa_verified_at: datetime | None
    last_login_at: datetime | None
    last_login_ip: str | None
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None

    model_config = ConfigDict(from_attributes=True)


class GlobalSuperCreateResponse(GlobalSuperRead):
    provisioning_uri: str

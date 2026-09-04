from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GlobalSuperCreate(BaseModel):
    dni: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=30)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    send_email: bool = True


class GlobalSuperUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=30)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    is_active: bool | None = None


class GlobalSuperRead(BaseModel):
    id: int
    dni: str | None
    name: str | None
    phone: str | None
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
    email_sent: bool = False


class GlobalSuperMfaProvisioningResponse(BaseModel):
    id: int
    email: EmailStr
    provisioning_uri: str

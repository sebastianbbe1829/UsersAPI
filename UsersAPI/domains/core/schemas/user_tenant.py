from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserTenantCreate(BaseModel):
    user_id: int
    tenant_id: int
    email: EmailStr = Field(
        description="Correo del usuario dentro del tenant"
    )

    password: str = Field(
        min_length=6,
        description="Contraseña del usuario dentro del tenant"
    )

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
    )

class UserTenantRead(BaseModel):
    id: int
    user_id: int
    tenant_id: int
    email: EmailStr
    phone: str | None
    status: int
    created_at: datetime
    created_by: str
    model_config = ConfigDict(
        from_attributes=True
    )

class UserTenantDeleteResponse(BaseModel):
    id: int
    user_id: int
    tenant_id: int
    status: int
    message: str
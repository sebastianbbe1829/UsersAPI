from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nombre del tenant",
        examples=["Empresa ABC"],
    )

    slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Identificador único del tenant",
        examples=["empresa-abc"],
    )


class TenantUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Nuevo nombre del tenant",
    )

    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Nuevo slug del tenant",
    )

    status: int | None = Field(
        default=None,
        description="Estado del tenant: 1 activo, 0 inactivo",
    )


class TenantRead(BaseModel):
    id: int
    name: str
    slug: str
    status: int
    created_at: datetime
    created_by: str

    model_config = ConfigDict(from_attributes=True)


class TenantDeleteResponse(BaseModel):
    id: int
    name: str
    slug: str
    status: int
    message: str


# ============================================================
# BOOTSTRAP
# ============================================================

class BootstrapRequest(BaseModel):

    tenant_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nombre del tenant",
        examples=["Empresa ABC"],
    )

    tenant_slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Identificador único del tenant",
        examples=["empresa-abc"],
    )

    admin_dni: str = Field(
        ...,
        min_length=5,
        max_length=20,
        description="DNI del administrador inicial",
    )

    admin_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nombre del administrador inicial",
    )

    admin_email: EmailStr = Field(
        ...,
        description="Correo del administrador dentro del tenant",
    )

    admin_password: str = Field(
        ...,
        min_length=6,
        description="Contraseña inicial del administrador",
    )

    admin_phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
        description="Teléfono del administrador",
    )


# ============================================================
# RESPUESTA BOOTSTRAP
# ============================================================

class BootstrapResponse(BaseModel):

    tenant_id: int
    tenant_name: str
    tenant_slug: str

    user_id: int
    user_dni: str
    user_name: str

    user_tenant_id: int
    user_email: EmailStr

    role_id: int
    role_code: str
    role_name: str

    message: str

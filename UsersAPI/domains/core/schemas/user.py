from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================
# DATOS GLOBALES DEL USUARIO
# ============================================================

class UserBase(BaseModel):
    dni: str = Field(
        min_length=5,
        max_length=20,
        description="DNI del usuario",
    )

    name: str = Field(
        min_length=2,
        max_length=100,
        description="Nombre del usuario",
    )


# ============================================================
# CREAR USUARIO
#
# app_users:
#   dni
#   name
#
# user_tenants:
#   email
#   password
#   phone
#   status
# ============================================================

class UserCreate(UserBase):

    email: EmailStr = Field(
        description="Correo electrónico del usuario dentro del tenant",
    )

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
        description="Teléfono del usuario dentro del tenant",
    )

    password: str = Field(
        min_length=6,
        description="Contraseña del usuario dentro del tenant",
    )

    status: int = Field(
        default=0,
        description=(
            "Estado del usuario dentro del tenant: "
            "0=inactivo, 1=activo, 3=eliminado lógicamente"
        ),
    )


# ============================================================
# ACTUALIZAR USUARIO
#
# Todos los campos son opcionales porque utilizamos PATCH.
# ============================================================

class UserUpdate(BaseModel):

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Nuevo nombre del usuario",
    )

    email: EmailStr | None = Field(
        default=None,
        description="Nuevo correo electrónico",
    )

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
        description="Nuevo teléfono",
    )

    password: str | None = Field(
        default=None,
        min_length=6,
        description="Nueva contraseña",
    )

    status: int | None = Field(
        default=None,
        description=(
            "Nuevo estado dentro del tenant: "
            "0=inactivo, 1=activo, 3=eliminado lógicamente"
        ),
    )

    unlock: bool | None = Field(
        default=None,
        description=(
            "Desbloquea la cuenta y reinicia los intentos fallidos "
            "de autenticación"
        ),
    )


# ============================================================
# RESPUESTA DE USUARIO
#
# La respuesta combina:
#
# app_users
#   dni
#   name
#
# user_tenants
#   email
#   phone
#   status
# ============================================================

class UserRead(UserBase):

    email: EmailStr = Field(
        description="Correo electrónico del usuario",
    )

    phone: str | None = Field(
        default=None,
        description="Teléfono del usuario",
    )

    status: int = Field(
        description=(
            "Estado del usuario dentro del tenant: "
            "0=inactivo, 1=activo, 3=eliminado lógicamente"
        ),
    )

    id: int = Field(
        description=(
            "Id del usuario"
        ),
    )

    failed_login_attempts: int = Field(
        default=0,
        description="Cantidad de intentos fallidos de autenticación",
    )

    locked_at: datetime | None = Field(
        default=None,
        description="Fecha y hora en que la cuenta fue bloqueada",
    )

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================
# RESPUESTA ELIMINACIÓN
# ============================================================

class UserDeleteResponse(UserRead):

    message: str = Field(
        description="Mensaje de confirmación de eliminación",
    )


# ============================================================
# RESPUESTA ACTIVACIÓN
# ============================================================

class UserActivateResponse(UserRead):

    message: str = Field(
        description="Mensaje de confirmación de activación",
    )
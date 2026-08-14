from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    dni: str = Field(min_length=5, max_length=20, description="DNI del usuario")
    name: str = Field(min_length=2, max_length=100, description="Nombre del usuario")
    email: EmailStr = Field(description="Correo electrónico del usuario")
    phone: str | None = Field(default=None, min_length=7, max_length=20, description="Teléfono del usuario")


class UserCreate(UserBase):
    status: int = Field(default=0, description="Estado del usuario: 0=inactivo, 1=activo, 3=eliminado lógicamente")
    password: str = Field(min_length=6, description="Contraseña del usuario")


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    status: int | None = Field(default=None, description="Estado: 0=inactivo, 1=activo, 3=eliminado lógicamente")
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    password: str | None = Field(default=None, min_length=6)


class UserRead(UserBase):
    status: int = Field(description="Estado del usuario: 0=inactivo, 1=activo, 3=eliminado lógicamente")
    model_config = ConfigDict(from_attributes=True)


class UserDeleteResponse(UserBase):
    message: str = Field(description="Mensaje de confirmación de eliminación")

class UserActivateResponse(UserBase):
    message: str = Field(description="Mensaje de confirmación de activación")


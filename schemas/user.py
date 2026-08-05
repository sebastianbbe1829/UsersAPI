from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    dni: str = Field(min_length=5, max_length=20, description="DNI del usuario")
    name: str = Field(min_length=2, max_length=100, description="Nombre del usuario")
    email: EmailStr = Field(description="Correo electrónico del usuario")
    phone: str | None = Field(default=None, min_length=7, max_length=20, description="Teléfono del usuario")


class UserCreate(UserBase):
    status: bool = Field(default=True, description="Estado activo del usuario")
    password: str = Field(min_length=6, description="Contraseña del usuario")


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    status: bool | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    password: str | None = Field(default=None, min_length=6)


class UserRead(UserBase):
    status: bool = Field(description="Estado activo del usuario")
    model_config = ConfigDict(from_attributes=True)


class UserDeleteResponse(UserBase):
    message: str = Field(description="Mensaje de confirmación de eliminación")


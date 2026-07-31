from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    dni: str
    name: str
    email: EmailStr
    status: bool = True
    phone: str | None = None
    password: str  # 🔒 requerido al crear usuario


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    status: bool | None = None
    phone: str | None = None
    password: str | None = None  # opcional al actualizar


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

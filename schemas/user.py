from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    dni: str
    name: str
    email: EmailStr
    phone: str | None = None


class UserCreate(UserBase):
    status: bool = True
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    status: bool | None = None
    phone: str | None = None
    password: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)


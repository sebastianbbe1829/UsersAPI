from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
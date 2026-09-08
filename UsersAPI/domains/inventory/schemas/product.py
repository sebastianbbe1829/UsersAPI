from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    inventory_type_id: int
    active: bool = True
    brand: str | None = Field(default=None, max_length=100)
    presentation: str | None = Field(default=None, max_length=100)
    image_url: HttpUrl | None = None
    image_source: str | None = Field(default=None, max_length=30)
    image_source_url: HttpUrl | None = None
    image_credit: str | None = Field(default=None, max_length=200)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    inventory_type_id: int | None = None
    active: bool | None = None
    brand: str | None = Field(default=None, max_length=100)
    presentation: str | None = Field(default=None, max_length=100)
    image_url: HttpUrl | None = None
    image_source: str | None = Field(default=None, max_length=30)
    image_source_url: HttpUrl | None = None
    image_credit: str | None = Field(default=None, max_length=200)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    code: str
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None

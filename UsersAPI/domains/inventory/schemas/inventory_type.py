from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryTypeBase(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    active: bool = True


class InventoryTypeCreate(InventoryTypeBase):
    pass


class InventoryTypeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class InventoryTypeRead(InventoryTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None

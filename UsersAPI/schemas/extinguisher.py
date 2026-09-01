from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtinguisherCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    extinguisher_type: str = Field(..., min_length=1, max_length=50)
    capacity: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=150)
    last_recharge_date: date | None = None
    next_recharge_date: date | None = None
    last_hydrostatic_test_date: date | None = None
    next_hydrostatic_test_date: date | None = None
    status: str = Field(default="ACTIVE", max_length=30)
    is_stock: bool = False


class ExtinguisherUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=50)
    extinguisher_type: str | None = Field(None, min_length=1, max_length=50)
    capacity: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=150)
    last_recharge_date: date | None = None
    next_recharge_date: date | None = None
    last_hydrostatic_test_date: date | None = None
    next_hydrostatic_test_date: date | None = None
    status: str | None = Field(None, max_length=30)
    is_stock: bool | None = None
    active: bool | None = None


class ExtinguisherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    code: str
    extinguisher_type: str
    capacity: str | None
    location: str | None
    last_recharge_date: date | None
    next_recharge_date: date | None
    last_hydrostatic_test_date: date | None
    next_hydrostatic_test_date: date | None
    status: str
    is_stock: bool
    active: bool
    created_at: datetime
    updated_at: datetime | None


class ExtinguisherDeleteResponse(BaseModel):
    message: str
    id: int

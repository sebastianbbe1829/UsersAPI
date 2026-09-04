from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtinguisherInspectionItemCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    display_order: int = Field(default=0, ge=0)


class ExtinguisherInspectionItemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    display_order: int | None = Field(default=None, ge=0)
    active: bool | None = None


class ExtinguisherInspectionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime | None = None

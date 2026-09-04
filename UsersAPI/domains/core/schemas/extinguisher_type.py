from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtinguisherTypeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)


class ExtinguisherTypeUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=100)
    active: bool | None = None


class ExtinguisherTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    active: bool
    created_at: datetime
    updated_at: datetime | None

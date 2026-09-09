from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from .sale import SaleCustomerCreate, SaleItemCreate


class SaleDraftCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    customers: list[SaleCustomerCreate] = Field(default_factory=list)
    discount_percentage: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        max_digits=7,
        decimal_places=4,
    )
    alias: str | None = Field(default=None, max_length=100)


class SaleDraftRead(BaseModel):
    id: UUID
    tenant_id: int
    draft_number: str
    payload: dict
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"from_attributes": True}

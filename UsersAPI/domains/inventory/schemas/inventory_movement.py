from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MovementType = Literal["ENTRY", "EXIT"]


class InventoryMovementCreate(BaseModel):
    product_id: int
    movement_type: MovementType
    origin_type: str = Field(min_length=1, max_length=30)
    origin_id: UUID | None = None
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    unit_purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    profit_percentage: Decimal | None = Field(default=None, ge=0, max_digits=7, decimal_places=4)
    notes: str | None = Field(default=None, max_length=500)


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: int
    product_id: int
    movement_type: str
    origin_type: str
    origin_id: UUID | None
    quantity: Decimal
    unit_purchase_price: Decimal | None
    profit_percentage: Decimal | None
    balance_before: Decimal
    balance_after: Decimal
    notes: str | None
    created_at: datetime
    created_by: str

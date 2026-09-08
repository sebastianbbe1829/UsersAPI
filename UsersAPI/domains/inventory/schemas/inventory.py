from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    product_id: int
    quantity: Decimal
    purchase_price: Decimal | None
    profit_percentage: Decimal
    total_inventory: Decimal
    sale_price: Decimal | None
    created_at: datetime
    created_by: str
    updated_at: datetime | None
    updated_by: str | None

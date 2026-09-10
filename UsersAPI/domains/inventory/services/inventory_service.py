from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import InventoryDB
from ..repositories import InventoryRepository


MONEY_UNIT = Decimal("1")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_UNIT, rounding=ROUND_HALF_UP)


def _with_calculated_values(inventory: InventoryDB) -> InventoryDB:
    quantity = Decimal(inventory.quantity or 0)
    purchase_price = inventory.purchase_price
    profit_percentage = Decimal(inventory.profit_percentage or 0)
    inventory.total_inventory = quantity * Decimal(purchase_price or 0)
    inventory.sale_price = (
        _money(Decimal(purchase_price) * (Decimal("1") + profit_percentage))
        if purchase_price is not None
        else None
    )
    return inventory


def list_inventory(db: Session, tenant_id: int) -> list[InventoryDB]:
    return [_with_calculated_values(item) for item in InventoryRepository(db).list(tenant_id)]


def get_inventory(product_id: int, db: Session, tenant_id: int) -> InventoryDB:
    inventory = InventoryRepository(db).get_by_product(tenant_id, product_id)
    if inventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    return _with_calculated_values(inventory)

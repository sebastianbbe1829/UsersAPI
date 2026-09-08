from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import InventoryMovementDB
from ..repositories import InventoryMovementRepository, InventoryRepository, ProductRepository
from ..schemas import InventoryMovementCreate


ALLOWED_ORIGIN_TYPES = {
    "PURCHASE",
    "SALE",
    "MANUAL_ADJUSTMENT",
    "SALES_RETURN",
    "PURCHASE_RETURN",
}


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "system"
    )


def create_inventory_movement(
    data: InventoryMovementCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> InventoryMovementDB:
    origin_type = data.origin_type.strip().upper()
    if origin_type not in ALLOWED_ORIGIN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported inventory movement origin",
        )
    if origin_type == "SALE" and data.movement_type != "EXIT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SALE movements must be EXIT movements",
        )
    if origin_type == "PURCHASE" and data.movement_type != "ENTRY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PURCHASE movements must be ENTRY movements",
        )

    product = ProductRepository(db).get_by_id(tenant_id, data.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive products cannot receive inventory movements",
        )

    inventory_repository = InventoryRepository(db)
    inventory = inventory_repository.get_by_product(tenant_id, data.product_id, lock=True)
    if inventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")

    quantity = Decimal(data.quantity)
    before = Decimal(inventory.quantity or 0)
    if data.movement_type == "EXIT" and quantity > before:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient inventory for this movement",
        )

    after = before + quantity if data.movement_type == "ENTRY" else before - quantity
    now = datetime.now(UTC)
    actor = _actor_name(current_user)

    if data.movement_type == "ENTRY" and data.unit_purchase_price is not None:
        inventory.purchase_price = data.unit_purchase_price
    if data.profit_percentage is not None:
        inventory.profit_percentage = data.profit_percentage
    inventory.updated_at = now
    inventory.updated_by = actor
    inventory.quantity = after
    inventory_repository.save(inventory)

    movement = InventoryMovementDB(
        tenant_id=tenant_id,
        product_id=data.product_id,
        movement_type=data.movement_type,
        origin_type=origin_type,
        origin_id=data.origin_id,
        quantity=quantity,
        unit_purchase_price=data.unit_purchase_price,
        profit_percentage=data.profit_percentage,
        balance_before=before,
        balance_after=after,
        notes=data.notes.strip() if data.notes else None,
        created_at=now,
        created_by=actor,
    )
    return InventoryMovementRepository(db).add(movement)

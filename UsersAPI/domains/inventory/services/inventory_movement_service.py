from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import InventoryDB, InventoryMovementDB
from ..repositories import (
    InventoryMovementRepository,
    InventoryRepository,
    ProductRepository,
)
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


def _validate_origin(data: InventoryMovementCreate, origin_type: str) -> None:
    expected_types = {
        "PURCHASE": "ENTRY",
        "SALE": "EXIT",
        "SALES_RETURN": "ENTRY",
        "PURCHASE_RETURN": "EXIT",
    }
    expected_movement_type = expected_types.get(origin_type)
    if expected_movement_type and data.movement_type != expected_movement_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{origin_type} movements must be {expected_movement_type} movements",
        )
    if origin_type == "SALE" and data.origin_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SALE movements require origin_id",
        )
    if origin_type == "PURCHASE" and data.unit_purchase_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PURCHASE movements require unit_purchase_price",
        )


def _calculate_weighted_average_cost(
    current_quantity: Decimal,
    current_average_cost: Decimal | None,
    entry_quantity: Decimal,
    entry_unit_cost: Decimal,
) -> Decimal:
    if current_quantity <= 0 or current_average_cost is None:
        return entry_unit_cost

    total_current_cost = current_quantity * current_average_cost
    total_entry_cost = entry_quantity * entry_unit_cost
    total_quantity = current_quantity + entry_quantity
    return (total_current_cost + total_entry_cost) / total_quantity


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
    _validate_origin(data, origin_type)

    product = ProductRepository(db).get_by_id(tenant_id, data.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive products cannot receive inventory movements",
        )

    inventory_repository = InventoryRepository(db)
    inventory = inventory_repository.get_by_product(
        tenant_id,
        data.product_id,
        lock=True,
    )
    quantity = Decimal(data.quantity)

    # Products are created without an inventory row. The first ENTRY creates
    # the stock record as part of the movement itself, keeping product creation
    # free of stock changes.
    if inventory is None:
        if data.movement_type == "EXIT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient inventory for this movement",
            )
        inventory = InventoryDB(
            tenant_id=tenant_id,
            product_id=data.product_id,
            quantity=Decimal("0"),
            purchase_price=None,
            profit_percentage=Decimal("0"),
            created_by=_actor_name(current_user),
        )
        inventory_repository.add(inventory)

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
        inventory.purchase_price = _calculate_weighted_average_cost(
            current_quantity=before,
            current_average_cost=inventory.purchase_price,
            entry_quantity=quantity,
            entry_unit_cost=data.unit_purchase_price,
        )
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


def list_inventory_movements(
    db: Session,
    tenant_id: int,
    product_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryMovementDB]:
    return InventoryMovementRepository(db).list_by_product(
        tenant_id,
        product_id,
        limit=limit,
        offset=offset,
    )


def get_inventory_movement(
    db: Session,
    tenant_id: int,
    movement_id: UUID,
) -> InventoryMovementDB:
    movement = InventoryMovementRepository(db).get_by_id(tenant_id, movement_id)
    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory movement not found",
        )
    return movement

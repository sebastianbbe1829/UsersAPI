from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import InventoryMovementDB
from ..repositories import InventoryMovementRepository
from ..schemas import InventoryMovementCreate
from ..services import create_inventory_movement


def create_movement(
    data: InventoryMovementCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    return create_inventory_movement(data, db, tenant_id, current_user)


def list_movements(
    product_id: int,
    db: Session,
    tenant_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[InventoryMovementDB]:
    return InventoryMovementRepository(db).list_by_product(
        tenant_id,
        product_id,
        limit=limit,
        offset=offset,
    )


def get_movement(
    movement_id: UUID,
    db: Session,
    tenant_id: int,
) -> InventoryMovementDB:
    movement = InventoryMovementRepository(db).get_by_id(tenant_id, movement_id)
    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory movement not found",
        )
    return movement

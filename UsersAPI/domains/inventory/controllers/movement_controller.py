from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import InventoryMovementDB
from ..schemas import InventoryMovementCreate
from ..services import (
    create_inventory_movement,
    get_inventory_movement,
    list_inventory_movements,
    reverse_inventory_movement,
)


def create_movement(data: InventoryMovementCreate, db: Session, tenant_id: int, current_user: object):
    return create_inventory_movement(data, db, tenant_id, current_user)


def reverse_movement(movement_id: UUID, quantity: Decimal | None, db: Session, tenant_id: int, current_user: object):
    return reverse_inventory_movement(movement_id, db, tenant_id, current_user, quantity)


def list_movements(product_id: int, db: Session, tenant_id: int, limit: int = 100, offset: int = 0) -> list[InventoryMovementDB]:
    return list_inventory_movements(db, tenant_id, product_id, limit=limit, offset=offset)


def get_movement(movement_id: UUID, db: Session, tenant_id: int) -> InventoryMovementDB:
    return get_inventory_movement(db, tenant_id, movement_id)

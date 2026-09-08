from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import InventoryMovementDB
from ..schemas import InventoryMovementCreate
from ..services import create_inventory_movement, get_inventory_movement, list_inventory_movements, reverse_inventory_movement
from ..services.inventory_export_service import export_movements_excel


def create_movement(data: InventoryMovementCreate, db: Session, tenant_id: int, current_user: object):
    return create_inventory_movement(data, db, tenant_id, current_user)


def reverse_movement(movement_id: UUID, quantity: Decimal | None, db: Session, tenant_id: int, current_user: object):
    return reverse_inventory_movement(movement_id, db, tenant_id, current_user, quantity)


def list_movements(product_id: int | None, db: Session, tenant_id: int, limit: int = 100, offset: int = 0, from_date: date | None = None, to_date: date | None = None) -> list[InventoryMovementDB]:
    movements = list_inventory_movements(db, tenant_id, product_id, limit=limit, offset=offset, from_date=from_date, to_date=to_date)
    movement_ids = [movement.id for movement in movements if movement.origin_type != "REVERSAL"]
    reversed_quantities = {}
    if movement_ids:
        rows = db.query(
            InventoryMovementDB.reversal_of_id,
            func.coalesce(func.sum(InventoryMovementDB.quantity), 0),
        ).filter(
            InventoryMovementDB.tenant_id == tenant_id,
            InventoryMovementDB.reversal_of_id.in_(movement_ids),
        ).group_by(InventoryMovementDB.reversal_of_id).all()
        reversed_quantities = {movement_id: Decimal(quantity) for movement_id, quantity in rows}

    for movement in movements:
        movement.reversed_quantity = reversed_quantities.get(movement.id, Decimal("0"))

    return movements


def get_movement(movement_id: UUID, db: Session, tenant_id: int) -> InventoryMovementDB:
    return get_inventory_movement(db, tenant_id, movement_id)


def export_movements(db: Session, tenant_id: int, product_id: int | None = None, from_date: date | None = None, to_date: date | None = None):
    return export_movements_excel(db, tenant_id, product_id, from_date, to_date)

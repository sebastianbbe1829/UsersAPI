from sqlalchemy.orm import Session

from ..services import get_inventory, list_inventory


def list_inventory_items(db: Session, tenant_id: int):
    return list_inventory(db, tenant_id)


def get_inventory_item(product_id: int, db: Session, tenant_id: int):
    return get_inventory(product_id, db, tenant_id)

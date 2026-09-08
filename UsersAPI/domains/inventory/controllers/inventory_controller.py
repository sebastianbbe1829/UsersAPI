from sqlalchemy.orm import Session

from ..services import get_inventory, list_inventory
from ..services.inventory_export_service import export_inventory_excel


def list_inventory_items(db: Session, tenant_id: int):
    return list_inventory(db, tenant_id)


def get_inventory_item(product_id: int, db: Session, tenant_id: int):
    return get_inventory(product_id, db, tenant_id)


def export_inventory(
    db: Session,
    tenant_id: int,
    search: str | None = None,
    inventory_type_id: int | None = None,
):
    return export_inventory_excel(db, tenant_id, search, inventory_type_id)

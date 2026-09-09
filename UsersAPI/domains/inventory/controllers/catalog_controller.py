from sqlalchemy.orm import Session

from ..schemas import InventoryTypeUpdate, ProductCreate, ProductUpdate
from ..services import (
    create_inventory_type,
    create_product,
    list_inventory_types,
    list_products,
    list_top_selling_products,
    update_inventory_type,
    update_product,
)


def create_type(data, db: Session, tenant_id: int, current_user: object):
    return create_inventory_type(data, db, tenant_id, current_user)


def list_types(db: Session, tenant_id: int, active_only: bool = False):
    return list_inventory_types(db, tenant_id, active_only)


def update_type(
    item_id: int,
    data: InventoryTypeUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    return update_inventory_type(item_id, data, db, tenant_id, current_user)


def create_product_item(data: ProductCreate, db: Session, tenant_id: int, current_user: object):
    return create_product(data, db, tenant_id, current_user)


def list_product_items(db: Session, tenant_id: int, active_only: bool = False):
    return list_products(db, tenant_id, active_only)


def list_top_selling_product_items(db: Session, tenant_id: int, limit: int = 6):
    return list_top_selling_products(db, tenant_id, limit=limit)


def update_product_item(
    item_id: int,
    data: ProductUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    return update_product(item_id, data, db, tenant_id, current_user)

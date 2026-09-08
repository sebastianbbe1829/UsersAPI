from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import ProductDB
from ..repositories import InventoryTypeRepository, ProductRepository
from ..schemas import ProductCreate, ProductUpdate


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "system"
    )


def _validate_inventory_type(
    db: Session,
    tenant_id: int,
    inventory_type_id: int,
) -> None:
    inventory_type = InventoryTypeRepository(db).get_by_id(tenant_id, inventory_type_id)
    if inventory_type is None or not inventory_type.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory type not found or inactive",
        )


def create_product(
    data: ProductCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> ProductDB:
    repository = ProductRepository(db)
    _validate_inventory_type(db, tenant_id, data.inventory_type_id)

    now = datetime.now(UTC)
    product = ProductDB(
        tenant_id=tenant_id,
        code=repository.next_code(tenant_id),
        name=data.name.strip(),
        inventory_type_id=data.inventory_type_id,
        active=data.active,
        created_at=now,
        created_by=_actor_name(current_user),
    )
    return repository.add(product)


def list_products(
    db: Session,
    tenant_id: int,
    active_only: bool = False,
) -> list[ProductDB]:
    return ProductRepository(db).list(tenant_id, active_only=active_only)


def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> ProductDB:
    repository = ProductRepository(db)
    product = repository.get_by_id(tenant_id, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    changes = data.model_dump(exclude_unset=True)
    if "name" in changes:
        product.name = changes["name"].strip()
    if "inventory_type_id" in changes:
        _validate_inventory_type(db, tenant_id, changes["inventory_type_id"])
        product.inventory_type_id = changes["inventory_type_id"]
    if "active" in changes:
        product.active = changes["active"]

    product.updated_at = datetime.now(UTC)
    product.updated_by = _actor_name(current_user)
    return repository.save(product)

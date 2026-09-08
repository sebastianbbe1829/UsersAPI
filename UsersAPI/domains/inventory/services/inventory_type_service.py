from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import InventoryTypeDB
from ..repositories import InventoryTypeRepository
from ..schemas import InventoryTypeCreate, InventoryTypeUpdate


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "system"
    )


def create_inventory_type(
    data: InventoryTypeCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> InventoryTypeDB:
    repository = InventoryTypeRepository(db)
    code = data.code.strip().upper()
    if repository.get_by_code(tenant_id, code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory type code already exists in this tenant",
        )
    inventory_type = InventoryTypeDB(
        tenant_id=tenant_id,
        code=code,
        name=data.name.strip(),
        active=data.active,
        created_at=datetime.now(UTC),
        created_by=_actor_name(current_user),
    )
    return repository.add(inventory_type)


def list_inventory_types(
    db: Session,
    tenant_id: int,
    active_only: bool = False,
) -> list[InventoryTypeDB]:
    return InventoryTypeRepository(db).list(tenant_id, active_only=active_only)


def update_inventory_type(
    inventory_type_id: int,
    data: InventoryTypeUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
) -> InventoryTypeDB:
    repository = InventoryTypeRepository(db)
    inventory_type = repository.get_by_id(tenant_id, inventory_type_id)
    if inventory_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory type not found",
        )

    changes = data.model_dump(exclude_unset=True)
    if "code" in changes:
        code = changes["code"].strip().upper()
        duplicate = repository.get_by_code(tenant_id, code)
        if duplicate is not None and duplicate.id != inventory_type.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventory type code already exists in this tenant",
            )
        inventory_type.code = code
    if "name" in changes:
        inventory_type.name = changes["name"].strip()
    if "active" in changes:
        inventory_type.active = changes["active"]

    inventory_type.updated_at = datetime.now(UTC)
    inventory_type.updated_by = _actor_name(current_user)
    return repository.save(inventory_type)

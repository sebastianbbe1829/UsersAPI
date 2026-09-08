from typing import cast
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers.catalog_controller import create_product_item, create_type, list_product_items, list_types, update_product_item, update_type
from ..controllers.inventory_controller import get_inventory_item, list_inventory_items
from ..controllers.movement_controller import create_movement, get_movement, list_movements, reverse_movement
from ..schemas import InventoryMovementCreate, InventoryMovementRead, InventoryRead, InventoryTypeCreate, InventoryTypeRead, InventoryTypeUpdate, ProductCreate, ProductRead, ProductUpdate

inventory_routes = APIRouter(prefix="/inventory", tags=["Inventarios"])

@inventory_routes.get("/types", response_model=list[InventoryTypeRead], dependencies=[Depends(require_permission("INVENTORY_READ"))])
async def list_inventory_types_route(active_only: bool = False, db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return list_types(db, cast(int, user_tenant.tenant_id), active_only)

@inventory_routes.post("/types", response_model=InventoryTypeRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("INVENTORY_CREATE"))])
async def create_inventory_type_route(data: InventoryTypeCreate, db: Session = Depends(get_db), current_user: UserTenantDB = Depends(get_current_user), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return create_type(data, db, cast(int, user_tenant.tenant_id), current_user)

@inventory_routes.patch("/types/{item_id}", response_model=InventoryTypeRead, dependencies=[Depends(require_permission("INVENTORY_UPDATE"))])
async def update_inventory_type_route(item_id: int, data: InventoryTypeUpdate, db: Session = Depends(get_db), current_user: UserTenantDB = Depends(get_current_user), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return update_type(item_id, data, db, cast(int, user_tenant.tenant_id), current_user)

@inventory_routes.get("/products", response_model=list[ProductRead], dependencies=[Depends(require_permission("INVENTORY_READ"))])
async def list_products_route(active_only: bool = False, db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return list_product_items(db, cast(int, user_tenant.tenant_id), active_only)

@inventory_routes.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("INVENTORY_CREATE"))])
async def create_product_route(data: ProductCreate, db: Session = Depends(get_db), current_user: UserTenantDB = Depends(get_current_user), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return create_product_item(data, db, cast(int, user_tenant.tenant_id), current_user)

@inventory_routes.patch("/products/{item_id}", response_model=ProductRead, dependencies=[Depends(require_permission("INVENTORY_UPDATE"))])
async def update_product_route(item_id: int, data: ProductUpdate, db: Session = Depends(get_db), current_user: UserTenantDB = Depends(get_current_user), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return update_product_item(item_id, data, db, cast(int, user_tenant.tenant_id), current_user)

@inventory_routes.get("", response_model=list[InventoryRead], dependencies=[Depends(require_permission("INVENTORY_READ"))])
async def list_inventory_route(db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return list_inventory_items(db, cast(int, user_tenant.tenant_id))

@inventory_routes.get("/products/{product_id}", response_model=InventoryRead, dependencies=[Depends(require_permission("INVENTORY_READ"))])
async def get_inventory_route(product_id: int, db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return get_inventory_item(product_id, db, cast(int, user_tenant.tenant_id))

@inventory_routes.post("/movements", response_model=InventoryMovementRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("INVENTORY_MOVEMENT_CREATE"))])
async def create_inventory_movement_route(data: InventoryMovementCreate, db: Session = Depends(get_db), current_user: UserTenantDB = Depends(get_current_user), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return create_movement(data, db, cast(int, user_tenant.tenant_id), current_user)

@inventory_routes.post("/movements/{movement_id}/reverse", response_model=InventoryMovementRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("INVENTORY_MOVEMENT_CREATE"))])
async def reverse_inventory_movement_route(movement_id: UUID, quantity: Decimal | None = Query(None, gt=0), db: Session = Depends(get_db), current_user: UserTenantDB = Depends(get_current_user), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return reverse_movement(movement_id, quantity, db, cast(int, user_tenant.tenant_id), current_user)

@inventory_routes.get("/movements", response_model=list[InventoryMovementRead], dependencies=[Depends(require_permission("INVENTORY_MOVEMENT_READ"))])
async def list_inventory_movements_route(product_id: int = Query(..., gt=0), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return list_movements(product_id, db, cast(int, user_tenant.tenant_id), limit=limit, offset=offset)

@inventory_routes.get("/movements/{movement_id}", response_model=InventoryMovementRead, dependencies=[Depends(require_permission("INVENTORY_MOVEMENT_READ"))])
async def get_inventory_movement_route(movement_id: UUID, db: Session = Depends(get_db), user_tenant: UserTenantDB = Depends(get_current_tenant)):
    return get_movement(movement_id, db, cast(int, user_tenant.tenant_id))

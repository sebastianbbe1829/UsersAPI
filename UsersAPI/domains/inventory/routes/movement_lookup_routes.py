from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers.catalog_controller import list_product_items
from ..schemas import ProductRead

movement_lookup_routes = APIRouter(prefix="/movements", tags=["Inventarios"])


@movement_lookup_routes.get(
    "/products",
    response_model=list[ProductRead],
    dependencies=[Depends(require_permission("INVENTORY_MOVEMENT_READ"))],
)
async def list_movement_products_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_product_items(db, cast(int, user_tenant.tenant_id), active_only=True)


@movement_lookup_routes.get(
    "/products-for-create",
    response_model=list[ProductRead],
    dependencies=[Depends(require_permission("INVENTORY_MOVEMENT_CREATE"))],
)
async def list_movement_products_for_create_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_product_items(db, cast(int, user_tenant.tenant_id), active_only=True)

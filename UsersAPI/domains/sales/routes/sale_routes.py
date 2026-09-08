from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..controllers import create, get, list_all
from ..schemas import SaleCreate, SaleRead

sales_routes = APIRouter(prefix="/sales", tags=["Ventas"])


@sales_routes.post(
    "",
    response_model=SaleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("SALES_CREATE"))],
)
async def create_sale_route(
    data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return create(data, db, cast(int, user_tenant.tenant_id), current_user)


@sales_routes.get(
    "",
    response_model=list[SaleRead],
    dependencies=[Depends(require_permission("SALES_READ"))],
)
async def list_sales_route(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_all(db, cast(int, user_tenant.tenant_id), limit=limit, offset=offset)


@sales_routes.get(
    "/{sale_id}",
    response_model=SaleRead,
    dependencies=[Depends(require_permission("SALES_READ"))],
)
async def get_sale_route(
    sale_id: UUID,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return get(sale_id, db, cast(int, user_tenant.tenant_id))

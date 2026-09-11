from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..schemas import CashAssignableUserRead
from ..services import list_assignable_users

cash_lookup_routes = APIRouter(prefix="/config", tags=["Caja"])


@cash_lookup_routes.get(
    "/assignable-users",
    response_model=list[CashAssignableUserRead],
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def list_assignable_users_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return list_assignable_users(db, cast(int, user_tenant.tenant_id))

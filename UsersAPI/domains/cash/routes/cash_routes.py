from typing import cast

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.controllers import get_current_user
from UsersAPI.domains.core.database import get_db
from UsersAPI.domains.core.models import UserTenantDB
from UsersAPI.security.dependencies import get_current_tenant
from UsersAPI.security.permissions import require_permission

from ..schemas import CashMovementCreate, CashRegisterClose, CashRegisterOpen, CashRegisterRead, CashRegisterSummary
from ..services import CashService


cash_routes = APIRouter(prefix="/cash", tags=["Caja"])


def _read_register(db: Session, tenant_id: int, register_id: int) -> CashRegisterRead:
    register = CashService.get_register(db, tenant_id, register_id)
    summary = CashService.summary(db, tenant_id, register_id)
    return CashRegisterRead.model_validate({**register.__dict__, "movements": register.movements, "summary": summary})


@cash_routes.post(
    "/registers/open",
    response_model=CashRegisterRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("CASH_CREATE"))],
)
async def open_register_route(
    data: CashRegisterOpen,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    register = CashService.open_register(data, db, cast(int, user_tenant.tenant_id), current_user)
    return _read_register(db, cast(int, user_tenant.tenant_id), register.id)


@cash_routes.get(
    "/registers/current",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def current_register_route(
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    register = CashService.get_current(db, cast(int, user_tenant.tenant_id))
    return _read_register(db, cast(int, user_tenant.tenant_id), register.id)


@cash_routes.get(
    "/registers",
    response_model=list[CashRegisterRead],
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def list_registers_route(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = cast(int, user_tenant.tenant_id)
    registers = CashService.list_registers(db, tenant_id, limit=limit, offset=offset)
    return [_read_register(db, tenant_id, register.id) for register in registers]


@cash_routes.get(
    "/registers/{register_id}",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def get_register_route(
    register_id: int,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return _read_register(db, cast(int, user_tenant.tenant_id), register_id)


@cash_routes.post(
    "/registers/{register_id}/movements",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_MOVEMENT_CREATE"))],
)
async def add_movement_route(
    register_id: int,
    data: CashMovementCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = cast(int, user_tenant.tenant_id)
    CashService.add_movement(data, db, tenant_id, register_id, current_user)
    return _read_register(db, tenant_id, register_id)


@cash_routes.post(
    "/registers/{register_id}/close",
    response_model=CashRegisterRead,
    dependencies=[Depends(require_permission("CASH_CLOSE"))],
)
async def close_register_route(
    register_id: int,
    data: CashRegisterClose,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    tenant_id = cast(int, user_tenant.tenant_id)
    CashService.close_register(data, db, tenant_id, register_id, current_user)
    return _read_register(db, tenant_id, register_id)


@cash_routes.get(
    "/registers/{register_id}/summary",
    response_model=CashRegisterSummary,
    dependencies=[Depends(require_permission("CASH_READ"))],
)
async def register_summary_route(
    register_id: int,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return CashService.summary(db, cast(int, user_tenant.tenant_id), register_id)

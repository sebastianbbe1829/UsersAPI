from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.models import UserTenantDB

from ..schemas import CashMovementCreate, CashRegisterClose, CashRegisterOpen
from ..services import CashService
from ..services.cash_context_service import require_operational_context


def open_register(
    data: CashRegisterOpen,
    db: Session,
    tenant_id: int,
    current_user: UserTenantDB,
):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "CASH_DAY_START_REQUIRED",
            "message": "Las cajas se abren automáticamente al iniciar el día operativo.",
        },
    )


def current_register(db: Session, tenant_id: int):
    return CashService.get_current(db, tenant_id)


def list_registers(db: Session, tenant_id: int, limit: int, offset: int):
    return CashService.list_registers(db, tenant_id, limit=limit, offset=offset)


def get_register(db: Session, tenant_id: int, register_id: int):
    return CashService.get_register(db, tenant_id, register_id)


def add_movement(
    data: CashMovementCreate,
    db: Session,
    tenant_id: int,
    register_id: int,
    current_user: UserTenantDB,
):
    require_operational_context(db, tenant_id, current_user)
    return CashService.add_movement(data, db, tenant_id, register_id, current_user)


def close_register(
    data: CashRegisterClose,
    db: Session,
    tenant_id: int,
    register_id: int,
    current_user: UserTenantDB,
):
    return CashService.close_register(data, db, tenant_id, register_id, current_user)


def register_summary(db: Session, tenant_id: int, register_id: int):
    return CashService.summary(db, tenant_id, register_id)

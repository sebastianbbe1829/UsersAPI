from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CashMovementDB, CashRegisterDB, UserCashAssignmentDB
from ..repositories import CashRepository


def _actor_name(current_user: object | None) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


def _require_assignment(db: Session, tenant_id: int, current_user: object) -> UserCashAssignmentDB:
    assignment = db.scalar(
        select(UserCashAssignmentDB).where(
            UserCashAssignmentDB.tenant_id == tenant_id,
            UserCashAssignmentDB.user_tenant_id == getattr(current_user, "id", None),
            UserCashAssignmentDB.status == 1,
        )
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "USER_CASH_REGISTER_NOT_ASSIGNED",
                "message": "El usuario no está asignado a ninguna sucursal y caja.",
            },
        )
    return assignment


def _require_open_register(db: Session, tenant_id: int, current_user: object) -> CashRegisterDB:
    assignment = _require_assignment(db, tenant_id, current_user)
    register = CashRepository.get_open(db, tenant_id, assignment.cash_box_id)
    if register is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "USER_CASH_REGISTER_CLOSED",
                "message": "La caja asignada al usuario está cerrada.",
            },
        )
    return register


def record_automatic_movement(
    db: Session,
    tenant_id: int,
    amount: Decimal,
    payment_method: str,
    origin_type: str,
    origin_id: object,
    description: str,
    current_user: object | None,
) -> CashMovementDB:
    register = _require_open_register(db, tenant_id, current_user)
    movement = CashMovementDB(
        tenant_id=tenant_id,
        cash_register_id=register.id,
        movement_type="INCOME" if amount >= 0 else "EXPENSE",
        amount=abs(Decimal(amount)),
        payment_method=payment_method.strip().upper(),
        origin_type=origin_type,
        origin_id=str(origin_id),
        description=description[:500],
        created_by=_actor_name(current_user),
    )
    db.add(movement)
    db.flush()
    return movement


def record_payment_reversal(
    db: Session,
    tenant_id: int,
    amount: Decimal,
    payment_method: str,
    payment_id: object,
    current_user: object | None,
) -> CashMovementDB:
    register = _require_open_register(db, tenant_id, current_user)
    movement = CashMovementDB(
        tenant_id=tenant_id,
        cash_register_id=register.id,
        movement_type="EXPENSE",
        amount=abs(Decimal(amount)),
        payment_method=payment_method.strip().upper(),
        origin_type="PAYMENT_REVERSAL",
        origin_id=str(payment_id),
        description=f"Anulación de pago de cartera {payment_id}"[:500],
        created_by=_actor_name(current_user),
    )
    db.add(movement)
    db.flush()
    return movement

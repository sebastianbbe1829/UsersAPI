from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CashMovementDB, CashRegisterDB
from ..repositories import CashRepository
from .cash_context_service import require_operational_context


def _actor_name(current_user: object | None) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


def _require_open_register(
    db: Session, tenant_id: int, current_user: object
) -> CashRegisterDB:
    context = require_operational_context(db, tenant_id, current_user)
    register = CashRepository.get_open(db, tenant_id, context["cash_box_id"])
    if register is None or register.id != context["register_id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_REGISTER_CLOSED",
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
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_CONTEXT_REQUIRED",
                "message": "La operación requiere un usuario con contexto de caja.",
            },
        )
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
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CASH_CONTEXT_REQUIRED",
                "message": "La operación requiere un usuario con contexto de caja.",
            },
        )
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

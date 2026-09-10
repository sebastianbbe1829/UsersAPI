from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import CashMovementDB
from ..repositories import CashRepository


CASH_METHODS = {"CASH", "EFECTIVO"}


def _actor_name(current_user: object | None) -> str:
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or getattr(current_user, "id", "system")
    )[:100]


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
    """Create an automatic cash movement in the currently open register.

    This helper intentionally participates in the caller's transaction. It does
    not commit. Sales and portfolio payments therefore remain atomic with the
    cash movement they originate.
    """
    register = CashRepository.get_open(db, tenant_id)
    if register is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay una caja abierta para registrar el movimiento.",
        )

    method = payment_method.strip().upper()
    movement_type = "INCOME" if amount >= 0 else "EXPENSE"
    movement = CashMovementDB(
        tenant_id=tenant_id,
        cash_register_id=register.id,
        movement_type=movement_type,
        amount=abs(Decimal(amount)),
        payment_method=method,
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
    """Reverse an already applied portfolio payment in the current register."""
    register = CashRepository.get_open(db, tenant_id)
    if register is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay una caja abierta para anular el movimiento de pago.",
        )

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

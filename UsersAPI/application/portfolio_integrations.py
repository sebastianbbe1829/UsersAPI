from decimal import Decimal

from sqlalchemy.orm import Session

from ..domains.cash.services.cash_movement_service import (
    record_automatic_movement,
    record_payment_reversal,
)


def record_portfolio_cash_movement(
    db: Session,
    tenant_id: int,
    amount: Decimal,
    payment_method: str,
    origin_id: object,
    description: str,
    current_user: object,
):
    return record_automatic_movement(
        db=db,
        tenant_id=tenant_id,
        amount=amount,
        payment_method=payment_method,
        origin_type="PORTFOLIO_PAYMENT",
        origin_id=origin_id,
        description=description,
        current_user=current_user,
    )


def reverse_portfolio_cash_movement(
    db: Session,
    tenant_id: int,
    amount: Decimal,
    payment_method: str,
    payment_id: object,
    current_user: object,
):
    return record_payment_reversal(
        db=db,
        tenant_id=tenant_id,
        amount=amount,
        payment_method=payment_method,
        payment_id=payment_id,
        current_user=current_user,
    )

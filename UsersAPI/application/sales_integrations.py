from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domains.cash.services.cash_movement_service import record_automatic_movement
from ..domains.clients.models import ClientDB
from ..domains.clients.services.compliance_override_service import has_compliance_override
from ..domains.inventory.schemas import InventoryMovementCreate
from ..domains.inventory.services.inventory_movement_service import create_inventory_movement
from ..domains.portfolio.models import CreditLimitDB, ObligationDB


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def client_is_eligible_for_sale(
    client: ClientDB,
    db: Session,
    tenant_id: int,
    compliance_override_checker=has_compliance_override,
) -> bool:
    if client.status != "ACTIVE":
        return False
    if client.is_listed or client.compliance_status == "MATCH":
        return compliance_override_checker(client.id, db, tenant_id)
    return True


def available_credit(client_id: UUID, db: Session, tenant_id: int) -> Decimal:
    credit_limit = db.scalar(
        select(CreditLimitDB)
        .where(
            CreditLimitDB.tenant_id == tenant_id,
            CreditLimitDB.client_id == client_id,
            CreditLimitDB.active.is_(True),
        )
        .with_for_update()
    )
    if credit_limit is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client does not have an active credit limit",
        )
    used = db.scalar(
        select(func.coalesce(func.sum(ObligationDB.balance), 0)).where(
            ObligationDB.tenant_id == tenant_id,
            ObligationDB.client_id == client_id,
            ObligationDB.status == "ACTIVE",
        )
    )
    return _money(
        max(
            Decimal("0"),
            Decimal(credit_limit.approved_limit) - Decimal(used or 0),
        )
    )


def record_sale_inventory_movement(
    data: InventoryMovementCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    return create_inventory_movement(data, db, tenant_id, current_user)


def record_sale_cash_movement(
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
        origin_type="SALE",
        origin_id=origin_id,
        description=description,
        current_user=current_user,
    )

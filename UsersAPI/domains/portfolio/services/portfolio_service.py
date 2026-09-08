from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from UsersAPI.domains.clients.models import ClientDB
from UsersAPI.domains.sales.models import SaleDB

from ..models import CreditLimitDB, ObligationDB, PaymentAllocationDB, PaymentDB
from ..repositories import PortfolioRepository
from ..schemas import CreditLimitUpdate, PaymentCreate

MONEY_UNIT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_UNIT, rounding=ROUND_HALF_UP)


def _actor_name(current_user: object | None) -> str:
    return (
        getattr(current_user, "email", None)
        or getattr(current_user, "username", None)
        or "system"
    )


def _client(db: Session, tenant_id: int, client_id: UUID, lock: bool = False) -> ClientDB:
    query = select(ClientDB).where(
        ClientDB.tenant_id == tenant_id,
        ClientDB.id == client_id,
    )
    if lock:
        query = query.with_for_update()
    client = db.scalar(query)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def _credit_read(credit_limit: CreditLimitDB, db: Session, tenant_id: int):
    used = _money(Decimal(PortfolioRepository(db).credit_used(tenant_id, credit_limit.client_id)))
    approved = _money(Decimal(credit_limit.approved_limit))
    credit_limit.credit_used = used
    credit_limit.credit_available = max(Decimal("0.00"), approved - used)
    return credit_limit


def get_client_credit(client_id: UUID, db: Session, tenant_id: int):
    _client(db, tenant_id, client_id)
    credit_limit = PortfolioRepository(db).get_credit_limit(tenant_id, client_id)
    if credit_limit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit limit not configured for client",
        )
    return _credit_read(credit_limit, db, tenant_id)


def upsert_client_credit_limit(
    client_id: UUID,
    data: CreditLimitUpdate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    _client(db, tenant_id, client_id)
    repository = PortfolioRepository(db)
    credit_limit = repository.get_credit_limit(tenant_id, client_id, lock=True)
    now = datetime.now(UTC)
    actor = _actor_name(current_user)
    if credit_limit is None:
        credit_limit = CreditLimitDB(
            tenant_id=tenant_id,
            client_id=client_id,
            approved_limit=_money(data.approved_limit),
            active=True,
            created_at=now,
            created_by=actor,
        )
        repository.add_credit_limit(credit_limit)
    else:
        used = _money(Decimal(repository.credit_used(tenant_id, client_id)))
        if _money(data.approved_limit) < used:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Credit limit cannot be lower than current credit used: {used}",
            )
        credit_limit.approved_limit = _money(data.approved_limit)
        credit_limit.active = True
        credit_limit.updated_at = now
        credit_limit.updated_by = actor
    db.flush()
    return _credit_read(credit_limit, db, tenant_id)


def list_obligations(db: Session, tenant_id: int):
    return PortfolioRepository(db).list_obligations(tenant_id)


def list_client_obligations(client_id: UUID, db: Session, tenant_id: int):
    _client(db, tenant_id, client_id)
    return PortfolioRepository(db).list_obligations(tenant_id, client_id=client_id)


def register_payment(
    data: PaymentCreate,
    db: Session,
    tenant_id: int,
    current_user: object,
):
    client = _client(db, tenant_id, data.client_id, lock=True)
    allocations_total = _money(
        sum((Decimal(item.amount) for item in data.allocations), Decimal("0"))
    )
    payment_amount = _money(data.amount)
    if allocations_total != payment_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment allocations must equal payment amount",
        )

    repository = PortfolioRepository(db)
    locked_obligations: list[ObligationDB] = []
    for allocation in data.allocations:
        obligation = repository.get_obligation(tenant_id, allocation.obligation_id, lock=True)
        if obligation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obligation not found",
            )
        if obligation.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Obligation does not belong to payment client",
            )
        if obligation.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only active obligations can receive payments",
            )
        amount = _money(allocation.amount)
        if amount > _money(obligation.balance):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment exceeds obligation balance: {obligation.balance}",
            )
        locked_obligations.append(obligation)

    payment = PaymentDB(
        tenant_id=tenant_id,
        client_id=client.id,
        payment_date=data.payment_date or date.today(),
        payment_method=data.payment_method.strip().upper(),
        amount=payment_amount,
        reference=data.reference.strip() if data.reference else None,
        notes=data.notes.strip() if data.notes else None,
        created_by=_actor_name(current_user),
    )
    repository.add_payment(payment)
    db.flush()

    for allocation_data, obligation in zip(data.allocations, locked_obligations):
        amount = _money(allocation_data.amount)
        obligation.balance = _money(Decimal(obligation.balance) - amount)
        obligation.updated_at = datetime.now(UTC)
        obligation.updated_by = _actor_name(current_user)
        if obligation.balance == Decimal("0.00"):
            obligation.status = "SETTLED"
            sale = db.scalar(
                select(SaleDB).where(
                    SaleDB.tenant_id == tenant_id,
                    SaleDB.id == obligation.sale_id,
                )
            )
            if sale is not None:
                sale.status = "COMPLETED"
                sale.updated_at = datetime.now(UTC)
                sale.updated_by = _actor_name(current_user)
        payment.allocations.append(
            PaymentAllocationDB(
                tenant_id=tenant_id,
                obligation_id=obligation.id,
                amount=amount,
            )
        )

    db.flush()
    return repository.get_payment(tenant_id, payment.id) or payment


def list_payments(db: Session, tenant_id: int, client_id: UUID | None = None):
    query = select(PaymentDB).options().where(PaymentDB.tenant_id == tenant_id)
    if client_id is not None:
        query = query.where(PaymentDB.client_id == client_id)
    return list(db.scalars(query.order_by(PaymentDB.payment_date.desc(), PaymentDB.created_at.desc())))

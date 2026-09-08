from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..models import CreditLimitDB, ObligationDB, PaymentDB


class PortfolioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_credit_limit(self, tenant_id: int, client_id: UUID, lock: bool = False):
        query = select(CreditLimitDB).where(
            CreditLimitDB.tenant_id == tenant_id,
            CreditLimitDB.client_id == client_id,
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def add_credit_limit(self, credit_limit: CreditLimitDB):
        self.db.add(credit_limit)
        return credit_limit

    def list_obligations(
        self,
        tenant_id: int,
        client_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        query = (
            select(ObligationDB)
            .options(joinedload(ObligationDB.sale))
            .where(ObligationDB.tenant_id == tenant_id)
        )
        if client_id is not None:
            query = query.where(ObligationDB.client_id == client_id)
        if date_from is not None:
            query = query.where(
                ObligationDB.created_at >= datetime.combine(date_from, time.min)
            )
        if date_to is not None:
            query = query.where(
                ObligationDB.created_at < datetime.combine(
                    date_to + timedelta(days=1), time.min
                )
            )
        return list(
            self.db.scalars(
                query.order_by(ObligationDB.created_at.desc())
            )
        )

    def get_obligation(self, tenant_id: int, obligation_id: UUID, lock: bool = False):
        query = select(ObligationDB).where(
            ObligationDB.tenant_id == tenant_id,
            ObligationDB.id == obligation_id,
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def get_obligation_by_sale(self, tenant_id: int, sale_id: UUID, lock: bool = False):
        query = select(ObligationDB).where(
            ObligationDB.tenant_id == tenant_id,
            ObligationDB.sale_id == sale_id,
        )
        if lock:
            query = query.with_for_update()
        return self.db.scalar(query)

    def add_obligation(self, obligation: ObligationDB):
        self.db.add(obligation)
        return obligation

    def add_payment(self, payment: PaymentDB):
        self.db.add(payment)
        return payment

    def get_payment(self, tenant_id: int, payment_id: UUID):
        return self.db.scalar(
            select(PaymentDB)
            .options(joinedload(PaymentDB.allocations))
            .where(PaymentDB.tenant_id == tenant_id, PaymentDB.id == payment_id)
        )

    def credit_used(self, tenant_id: int, client_id: UUID) -> object:
        value = self.db.scalar(
            select(func.coalesce(func.sum(ObligationDB.balance), 0)).where(
                ObligationDB.tenant_id == tenant_id,
                ObligationDB.client_id == client_id,
                ObligationDB.status == "ACTIVE",
            )
        )
        return value or 0

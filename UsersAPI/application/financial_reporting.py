from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domains.portfolio.models import PaymentDB
from ..domains.sales.models import SaleDB, SalePaymentDB

CREDIT_METHODS = ["CREDITO", "CREDIT", "CRÉDITO"]


def get_credit_sales_total(db: Session, tenant_id: int, business_date: date):
    return db.scalar(
        select(func.coalesce(func.sum(SalePaymentDB.amount), 0))
        .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
        .where(
            SalePaymentDB.tenant_id == tenant_id,
            SalePaymentDB.payment_method.in_(CREDIT_METHODS),
            SaleDB.business_date == business_date,
        )
    )


def get_sales_payment_rows(db: Session, tenant_id: int, business_date: date):
    return db.execute(
        select(SalePaymentDB.payment_method, SalePaymentDB.amount)
        .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
        .where(
            SalePaymentDB.tenant_id == tenant_id,
            SaleDB.tenant_id == tenant_id,
            SaleDB.business_date == business_date,
            SaleDB.status != "CANCELLED",
        )
    ).all()


def get_portfolio_payment_rows(db: Session, tenant_id: int, business_date: date):
    return db.execute(
        select(PaymentDB.payment_method, PaymentDB.amount, PaymentDB.status).where(
            PaymentDB.tenant_id == tenant_id,
            PaymentDB.payment_date == business_date,
        )
    ).all()


def get_credit_sales_by_register(db: Session, tenant_id: int, business_date: date):
    return db.execute(
        select(SalePaymentDB.sale_id, SalePaymentDB.amount, SalePaymentDB.cash_register_id)
        .join(SaleDB, SaleDB.id == SalePaymentDB.sale_id)
        .where(
            SalePaymentDB.tenant_id == tenant_id,
            SaleDB.tenant_id == tenant_id,
            SaleDB.business_date == business_date,
            SaleDB.status != "CANCELLED",
            SalePaymentDB.payment_method.in_(CREDIT_METHODS),
        )
    ).all()

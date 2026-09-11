import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class PaymentDB(Base):
    __tablename__ = "portfolio_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_portfolio_payments_amount"),
        CheckConstraint(
            "status IN ('APLICADO', 'ANULADO')",
            name="ck_portfolio_payments_status",
        ),
        CheckConstraint(
            "UPPER(payment_method) NOT IN ('CREDITO', 'CREDIT', 'CRÉDITO')",
            name="ck_portfolio_payments_method_not_credit",
        ),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id"),
        nullable=False,
        index=True,
    )
    cash_register_id = Column(
        Integer,
        ForeignKey("users_api.cash_registers.id"),
        nullable=True,
        index=True,
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.clients.id"),
        nullable=False,
        index=True,
    )
    payment_date = Column(Date, nullable=False, server_default=text("CURRENT_DATE"))
    payment_method = Column(String(30), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(
        String(20), nullable=False, server_default=text("'APLICADO'"), default="APLICADO"
    )
    reference = Column(String(100), nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)

    allocations = relationship(
        "PaymentAllocationDB",
        back_populates="payment",
        cascade="all, delete-orphan",
    )

    @property
    def business_date(self):
        """Payment date is the accounting/business date for legacy payments."""
        return self.payment_date


class PaymentAllocationDB(Base):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_allocations_amount"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id"),
        nullable=False,
        index=True,
    )
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.portfolio_payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    obligation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.obligations.id"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(18, 2), nullable=False)

    payment = relationship("PaymentDB", back_populates="allocations")

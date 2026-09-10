from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class CashDayDB(Base):
    __tablename__ = "cash_days"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_cash_days_tenant_id"),
        Index("uq_cash_days_tenant_date", "tenant_id", "business_date", unique=True),
        Index(
            "uq_cash_days_open_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
        Index("ix_cash_days_tenant_id", "tenant_id"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    business_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'OPEN'"))
    opened_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    opened_by = Column(String(100), nullable=False)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)
    closing_notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=True)

    branches = relationship(
        "CashDayBranchDB",
        back_populates="cash_day",
        cascade="all, delete-orphan",
        order_by="CashDayBranchDB.branch_id",
    )
    registers = relationship(
        "CashRegisterDB",
        back_populates="cash_day",
        order_by="CashRegisterDB.id",
    )

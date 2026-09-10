from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class CashRegisterDB(Base):
    __tablename__ = "cash_registers"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id"], ["users_api.tenants.id"]),
        UniqueConstraint("tenant_id", "id", name="uq_cash_registers_tenant_id"),
        Index("ix_cash_registers_tenant_id", "tenant_id"),
        Index(
            "uq_cash_registers_open_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    opened_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    opened_by = Column(String(100), nullable=False)
    opening_amount = Column(Numeric(18, 2), nullable=False, server_default=text("0"))
    status = Column(String(20), nullable=False, server_default=text("'OPEN'"))
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)
    expected_cash = Column(Numeric(18, 2), nullable=True)
    counted_cash = Column(Numeric(18, 2), nullable=True)
    difference = Column(Numeric(18, 2), nullable=True)
    closing_notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=True)

    movements = relationship(
        "CashMovementDB",
        back_populates="cash_register",
        cascade="all, delete-orphan",
        order_by="CashMovementDB.id",
    )

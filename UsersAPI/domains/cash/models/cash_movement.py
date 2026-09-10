from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class CashMovementDB(Base):
    __tablename__ = "cash_movements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "cash_register_id"],
            ["users_api.cash_registers.tenant_id", "users_api.cash_registers.id"],
        ),
        Index("ix_cash_movements_tenant_id", "tenant_id"),
        Index("ix_cash_movements_cash_register_id", "cash_register_id"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    cash_register_id = Column(Integer, nullable=False)
    movement_type = Column(String(20), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    payment_method = Column(String(30), nullable=True)
    origin_type = Column(String(30), nullable=False)
    origin_id = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)

    cash_register = relationship("CashRegisterDB", back_populates="movements")

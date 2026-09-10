from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKeyConstraint, Identity, Integer, Numeric, String, text

from UsersAPI.domains.core.database import Base


class CashRegisterDB(Base):
    __tablename__ = "cash_registers"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id"], ["users_api.tenants.id"]),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)
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

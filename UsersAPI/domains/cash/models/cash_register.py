from sqlalchemy import (
    Column,
    Date,
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
        ForeignKeyConstraint(
            ["tenant_id", "branch_id"],
            ["users_api.branches.tenant_id", "users_api.branches.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "cash_box_id"],
            ["users_api.cash_boxes.tenant_id", "users_api.cash_boxes.id"],
        ),
        UniqueConstraint("tenant_id", "id", name="uq_cash_registers_tenant_id"),
        Index("ix_cash_registers_tenant_id", "tenant_id"),
        Index("ix_cash_registers_branch_id", "branch_id"),
        Index("ix_cash_registers_cash_box_id", "cash_box_id"),
        Index(
            "uq_cash_registers_open_box",
            "cash_box_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
        Index(
            "uq_cash_registers_box_business_date",
            "cash_box_id",
            "business_date",
            unique=True,
        ),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    branch_id = Column(Integer, nullable=True)
    cash_box_id = Column(Integer, nullable=True)
    business_date = Column(Date, nullable=True)
    opened_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    opened_by = Column(String(100), nullable=False)
    opening_amount = Column(
        Numeric(18, 2), nullable=False, server_default=text("0")
    )
    status = Column(String(20), nullable=False, server_default=text("'OPEN'"))
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)
    expected_cash = Column(Numeric(18, 2), nullable=True)
    counted_cash = Column(Numeric(18, 2), nullable=True)
    difference = Column(Numeric(18, 2), nullable=True)
    closing_notes = Column(String(500), nullable=True)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(DateTime, nullable=True)

    movements = relationship(
        "CashMovementDB",
        back_populates="cash_register",
        cascade="all, delete-orphan",
        order_by="CashMovementDB.id",
    )

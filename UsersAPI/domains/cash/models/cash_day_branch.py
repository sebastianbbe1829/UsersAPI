from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class CashDayBranchDB(Base):
    __tablename__ = "cash_day_branches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "cash_day_id"],
            ["users_api.cash_days.tenant_id", "users_api.cash_days.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "branch_id"],
            ["users_api.branches.tenant_id", "branches.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tenant_id", "cash_day_id", "branch_id",
            name="uq_cash_day_branches_day_branch",
        ),
        Index("ix_cash_day_branches_tenant_id", "tenant_id"),
        Index("ix_cash_day_branches_cash_day_id", "cash_day_id"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    cash_day_id = Column(Integer, nullable=False)
    branch_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'OPEN'"))
    opened_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    opened_by = Column(String(100), nullable=False)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=True)

    cash_day = relationship("CashDayDB", back_populates="branches")
    branch = relationship("BranchDB")

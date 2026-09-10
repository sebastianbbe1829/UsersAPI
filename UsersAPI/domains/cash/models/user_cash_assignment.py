from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class UserCashAssignmentDB(Base):
    __tablename__ = "user_cash_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "user_tenant_id"],
            ["users_api.user_tenants.tenant_id", "users_api.user_tenants.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "branch_id"],
            ["users_api.branches.tenant_id", "users_api.branches.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "cash_box_id"],
            ["users_api.cash_boxes.tenant_id", "users_api.cash_boxes.id"],
        ),
        Index(
            "uq_user_cash_assignments_active_user",
            "tenant_id",
            "user_tenant_id",
            unique=True,
            postgresql_where=text("status = 1"),
        ),
        Index("ix_user_cash_assignments_tenant_id", "tenant_id"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    user_tenant_id = Column(Integer, nullable=False)
    branch_id = Column(Integer, nullable=False)
    cash_box_id = Column(Integer, nullable=False)
    status = Column(Integer, nullable=False, server_default=text("1"))
    assigned_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    assigned_by = Column(String(100), nullable=False)
    unassigned_at = Column(DateTime, nullable=True)
    unassigned_by = Column(String(100), nullable=True)

    branch = relationship("BranchDB", back_populates="user_assignments")
    cash_box = relationship("CashBoxDB", back_populates="assignments")

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


class CashBoxDB(Base):
    __tablename__ = "cash_boxes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "branch_id"],
            ["users_api.branches.tenant_id", "users_api.branches.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_cash_boxes_tenant_id"),
        Index("uq_cash_boxes_branch_code", "branch_id", "code", unique=True),
        Index("ix_cash_boxes_tenant_id", "tenant_id"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    branch_id = Column(Integer, nullable=False)
    code = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    branch = relationship("BranchDB", back_populates="cash_boxes")
    assignments = relationship(
        "UserCashAssignmentDB",
        back_populates="cash_box",
        cascade="all, delete-orphan",
    )

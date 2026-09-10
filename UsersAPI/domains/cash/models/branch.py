from sqlalchemy import Column, DateTime, ForeignKey, Identity, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class BranchDB(Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_branches_tenant_id"),
        Index("uq_branches_tenant_code", "tenant_id", "code", unique=True),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(30), nullable=False)
    name = Column(String(150), nullable=False)
    address = Column(String(250), nullable=True)
    phone = Column(String(30), nullable=True)
    status = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    cash_boxes = relationship("CashBoxDB", back_populates="branch", cascade="all, delete-orphan")
    user_assignments = relationship("UserCashAssignmentDB", back_populates="branch", cascade="all, delete-orphan")

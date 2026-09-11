import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from UsersAPI.domains.core.database import Base


class CreditLimitDB(Base):
    __tablename__ = "credit_limits"
    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", name="uq_credit_limits_tenant_client"),
        CheckConstraint("approved_limit >= 0", name="ck_credit_limits_approved_limit"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id"),
        nullable=False,
        index=True,
    )
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.clients.id"),
        nullable=False,
        index=True,
    )
    approved_limit = Column(Numeric(18, 2), nullable=False, server_default=text("0"))
    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ObligationDB(Base):
    __tablename__ = "obligations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sale_id", name="uq_obligations_tenant_sale"),
        CheckConstraint("initial_amount > 0", name="ck_obligations_initial_amount"),
        CheckConstraint(
            "balance >= 0 AND balance <= initial_amount",
            name="ck_obligations_balance",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'SETTLED', 'CANCELLED')",
            name="ck_obligations_status",
        ),
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
    sale_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.sales.id"),
        nullable=False,
        index=True,
    )
    business_date = Column(Date, nullable=False, index=True)
    initial_amount = Column(Numeric(18, 2), nullable=False)
    balance = Column(Numeric(18, 2), nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'ACTIVE'"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    sale = relationship("SaleDB", back_populates="obligation")

    @property
    def sale_number(self) -> str | None:
        return self.sale.sale_number if self.sale is not None else None

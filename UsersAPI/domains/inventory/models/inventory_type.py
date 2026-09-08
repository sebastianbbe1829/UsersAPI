from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class InventoryTypeDB(Base):
    __tablename__ = "inventory_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_inventory_types_tenant_code"),
        UniqueConstraint("tenant_id", "id", name="uq_inventory_types_tenant_id"),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id"), nullable=False, index=True)
    code = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    products = relationship("ProductDB", back_populates="inventory_type")

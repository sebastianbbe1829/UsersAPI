from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ProductDB(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_products_tenant_code"),
        UniqueConstraint("tenant_id", "id", name="uq_products_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "inventory_type_id"],
            ["users_api.inventory_types.tenant_id", "users_api.inventory_types.id"],
        ),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id"), nullable=False, index=True)
    inventory_type_id = Column(Integer, nullable=False, index=True)
    code = Column(String(30), nullable=False)
    name = Column(String(150), nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    inventory_type = relationship("InventoryTypeDB", back_populates="products")
    inventory = relationship("InventoryDB", back_populates="product", uselist=False)
    movements = relationship("InventoryMovementDB", back_populates="product")

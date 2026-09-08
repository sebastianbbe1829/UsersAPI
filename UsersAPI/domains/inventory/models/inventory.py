from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class InventoryDB(Base):
    __tablename__ = "inventories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_id", name="uq_inventories_tenant_product"),
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["users_api.products.tenant_id", "users_api.products.id"],
        ),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Numeric(18, 3), nullable=False, server_default=text("0"))
    purchase_price = Column(Numeric(18, 2), nullable=True)
    profit_percentage = Column(Numeric(7, 4), nullable=False, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    product = relationship("ProductDB", back_populates="inventory")

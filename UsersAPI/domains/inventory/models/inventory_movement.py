import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class InventoryMovementDB(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["users_api.products.tenant_id", "users_api.products.id"],
        ),
        ForeignKeyConstraint(
            ["reversal_of_id"],
            ["users_api.inventory_movements.id"],
        ),
        CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        CheckConstraint(
            "movement_type IN ('ENTRY', 'EXIT', 'ADJUSTMENT')",
            name="ck_inventory_movements_type",
        ),
        CheckConstraint(
            "balance_before >= 0 AND balance_after >= 0",
            name="ck_inventory_movements_balances_non_negative",
        ),
        Index(
            "ix_users_api_inventory_movements_origin",
            "origin_type",
            "origin_id",
        ),
        Index(
            "ix_users_api_inventory_movements_reversal_of_id",
            "reversal_of_id",
        ),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    movement_type = Column(String(20), nullable=False)
    origin_type = Column(String(30), nullable=False)
    origin_id = Column(UUID(as_uuid=True), nullable=True)
    reversal_of_id = Column(UUID(as_uuid=True), nullable=True)
    quantity = Column(Numeric(18, 3), nullable=False)
    unit_purchase_price = Column(Numeric(18, 2), nullable=True)
    profit_percentage = Column(Numeric(7, 4), nullable=True)
    balance_before = Column(Numeric(18, 3), nullable=False)
    balance_after = Column(Numeric(18, 3), nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)

    product = relationship("ProductDB", back_populates="movements")
    reversal_of = relationship(
        "InventoryMovementDB",
        remote_side=[id],
        foreign_keys=[reversal_of_id],
    )

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class SaleDB(Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sale_number", name="uq_sales_tenant_number"),
        CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100", name="ck_sales_discount_percentage"),
        CheckConstraint("subtotal >= 0 AND discount_amount >= 0 AND total >= 0", name="ck_sales_amounts"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id"), nullable=False, index=True)
    sale_number = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'COMPLETED'"))
    subtotal = Column(Numeric(18, 2), nullable=False)
    discount_percentage = Column(Numeric(7, 4), nullable=False, server_default=text("0"))
    discount_amount = Column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    items = relationship("SaleItemDB", back_populates="sale", cascade="all, delete-orphan")
    customers = relationship("SaleCustomerDB", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("SalePaymentDB", back_populates="sale", cascade="all, delete-orphan")


class SaleItemDB(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "product_id"], ["users_api.products.tenant_id", "users_api.products.id"]),
        CheckConstraint("quantity > 0", name="ck_sale_items_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_sale_items_unit_price"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("users_api.sales.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    product_code = Column(String(30), nullable=False)
    product_name = Column(String(150), nullable=False)
    quantity = Column(Numeric(18, 3), nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    line_total = Column(Numeric(18, 2), nullable=False)

    sale = relationship("SaleDB", back_populates="items")


class SaleCustomerDB(Base):
    __tablename__ = "sale_customers"
    __table_args__ = (
        CheckConstraint("allocation_percentage > 0 AND allocation_percentage <= 100", name="ck_sale_customers_percentage"),
        CheckConstraint("allocation_amount > 0", name="ck_sale_customers_amount"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("users_api.sales.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users_api.clients.id"), nullable=True, index=True)
    customer_name = Column(String(250), nullable=False)
    allocation_percentage = Column(Numeric(7, 4), nullable=False)
    allocation_amount = Column(Numeric(18, 2), nullable=False)
    is_generic = Column(Boolean, nullable=False, server_default=text("false"))

    sale = relationship("SaleDB", back_populates="customers")


class SalePaymentDB(Base):
    __tablename__ = "sale_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_sale_payments_amount"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("users_api.sales.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    payment_method = Column(String(30), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)

    sale = relationship("SaleDB", back_populates="payments")

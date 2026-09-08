"""create sales domain

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("sale_number", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'COMPLETED'"), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("discount_percentage", sa.Numeric(7, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100", name="ck_sales_discount_percentage"),
        sa.CheckConstraint("subtotal >= 0 AND discount_amount >= 0 AND total >= 0", name="ck_sales_amounts"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "sale_number", name="uq_sales_tenant_number"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_sales_tenant_id", "sales", ["tenant_id"], schema=SCHEMA)

    op.create_table(
        "sale_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(length=30), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sale_items_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_items_unit_price"),
        sa.ForeignKeyConstraint(["sale_id"], [f"{SCHEMA}.sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "product_id"], [f"{SCHEMA}.products.tenant_id", f"{SCHEMA}.products.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_sale_items_sale_id", "sale_items", ["sale_id"], schema=SCHEMA)
    op.create_index("ix_users_api_sale_items_tenant_id", "sale_items", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_sale_items_product_id", "sale_items", ["product_id"], schema=SCHEMA)

    op.create_table(
        "sale_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_name", sa.String(length=250), nullable=False),
        sa.Column("allocation_percentage", sa.Numeric(7, 4), nullable=False),
        sa.Column("allocation_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("is_generic", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("allocation_percentage > 0 AND allocation_percentage <= 100", name="ck_sale_customers_percentage"),
        sa.CheckConstraint("allocation_amount > 0", name="ck_sale_customers_amount"),
        sa.ForeignKeyConstraint(["sale_id"], [f"{SCHEMA}.sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], [f"{SCHEMA}.clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_sale_customers_sale_id", "sale_customers", ["sale_id"], schema=SCHEMA)
    op.create_index("ix_users_api_sale_customers_tenant_id", "sale_customers", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_sale_customers_client_id", "sale_customers", ["client_id"], schema=SCHEMA)

    op.create_table(
        "sale_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_sale_payments_amount"),
        sa.ForeignKeyConstraint(["sale_id"], [f"{SCHEMA}.sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_sale_payments_sale_id", "sale_payments", ["sale_id"], schema=SCHEMA)
    op.create_index("ix_users_api_sale_payments_tenant_id", "sale_payments", ["tenant_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_users_api_sale_payments_tenant_id", table_name="sale_payments", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_payments_sale_id", table_name="sale_payments", schema=SCHEMA)
    op.drop_table("sale_payments", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_customers_client_id", table_name="sale_customers", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_customers_tenant_id", table_name="sale_customers", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_customers_sale_id", table_name="sale_customers", schema=SCHEMA)
    op.drop_table("sale_customers", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_items_product_id", table_name="sale_items", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_items_tenant_id", table_name="sale_items", schema=SCHEMA)
    op.drop_index("ix_users_api_sale_items_sale_id", table_name="sale_items", schema=SCHEMA)
    op.drop_table("sale_items", schema=SCHEMA)
    op.drop_index("ix_users_api_sales_tenant_id", table_name="sales", schema=SCHEMA)
    op.drop_table("sales", schema=SCHEMA)

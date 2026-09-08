"""create inventory domain tables

Revision ID: b7c4d5e6f7a8
Revises: 8c5d7e9f1a2b
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "8c5d7e9f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.create_table(
        "inventory_types",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_inventory_types_tenant_code"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_inventory_types_tenant_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventory_types_tenant_id",
        "inventory_types",
        ["tenant_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("inventory_type_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "inventory_type_id"],
            [f"{SCHEMA}.inventory_types.tenant_id", f"{SCHEMA}.inventory_types.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_products_tenant_code"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_products_tenant_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_products_tenant_id",
        "products",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_products_inventory_type_id",
        "products",
        ["inventory_type_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "inventories",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False, server_default=sa.text("0")),
        sa.Column("purchase_price", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("profit_percentage", sa.Numeric(precision=7, scale=4), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            [f"{SCHEMA}.products.tenant_id", f"{SCHEMA}.products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "product_id", name="uq_inventories_tenant_product"),
        sa.CheckConstraint("quantity >= 0", name="ck_inventories_quantity_non_negative"),
        sa.CheckConstraint(
            "profit_percentage >= 0",
            name="ck_inventories_profit_percentage_non_negative",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventories_tenant_id",
        "inventories",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventories_product_id",
        "inventories",
        ["product_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("origin_type", sa.String(length=30), nullable=False),
        sa.Column("origin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("unit_purchase_price", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("profit_percentage", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("balance_before", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            [f"{SCHEMA}.products.tenant_id", f"{SCHEMA}.products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        sa.CheckConstraint(
            "movement_type IN ('ENTRY', 'EXIT', 'ADJUSTMENT')",
            name="ck_inventory_movements_type",
        ),
        sa.CheckConstraint(
            "balance_before >= 0 AND balance_after >= 0",
            name="ck_inventory_movements_balances_non_negative",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventory_movements_tenant_id",
        "inventory_movements",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventory_movements_product_id",
        "inventory_movements",
        ["product_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventory_movements_origin",
        "inventory_movements",
        ["origin_type", "origin_id"],
        schema=SCHEMA,
    )

    for table in ("inventory_types", "products", "inventories", "inventory_movements"):
        op.execute(f"ALTER TABLE {SCHEMA}.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {SCHEMA}.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""CREATE POLICY {table}_tenant_isolation ON {SCHEMA}.{table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)"""
        )


def downgrade() -> None:
    for table in ("inventory_movements", "inventories", "products", "inventory_types"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {SCHEMA}.{table}")
        op.execute(f"ALTER TABLE {SCHEMA}.{table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {SCHEMA}.{table} DISABLE ROW LEVEL SECURITY")

    for index_name, table_name in (
        ("ix_users_api_inventory_movements_origin", "inventory_movements"),
        ("ix_users_api_inventory_movements_product_id", "inventory_movements"),
        ("ix_users_api_inventory_movements_tenant_id", "inventory_movements"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("inventory_movements", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_inventories_product_id", "inventories"),
        ("ix_users_api_inventories_tenant_id", "inventories"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("inventories", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_products_inventory_type_id", "products"),
        ("ix_users_api_products_tenant_id", "products"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("products", schema=SCHEMA)

    op.drop_index(
        "ix_users_api_inventory_types_tenant_id",
        table_name="inventory_types",
        schema=SCHEMA,
    )
    op.drop_table("inventory_types", schema=SCHEMA)

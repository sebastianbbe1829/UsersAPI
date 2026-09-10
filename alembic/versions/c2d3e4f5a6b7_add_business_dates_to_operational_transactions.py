"""add business dates to operational transactions

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("business_date", sa.Date(), nullable=True),
        schema="users_api",
    )
    op.add_column(
        "obligations",
        sa.Column("business_date", sa.Date(), nullable=True),
        schema="users_api",
    )
    op.add_column(
        "inventory_movements",
        sa.Column("business_date", sa.Date(), nullable=True),
        schema="users_api",
    )
    op.add_column(
        "cash_movements",
        sa.Column("business_date", sa.Date(), nullable=True),
        schema="users_api",
    )

    op.execute(
        """
        UPDATE users_api.sales
        SET business_date = created_at::date
        WHERE business_date IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.obligations o
        SET business_date = s.business_date
        FROM users_api.sales s
        WHERE o.sale_id = s.id
          AND o.business_date IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.obligations
        SET business_date = created_at::date
        WHERE business_date IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.inventory_movements
        SET business_date = created_at::date
        WHERE business_date IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.cash_movements cm
        SET business_date = cr.business_date
        FROM users_api.cash_registers cr
        WHERE cm.tenant_id = cr.tenant_id
          AND cm.cash_register_id = cr.id
          AND cm.business_date IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.cash_movements
        SET business_date = created_at::date
        WHERE business_date IS NULL
        """
    )

    op.alter_column("sales", "business_date", nullable=False, schema="users_api")
    op.alter_column("obligations", "business_date", nullable=False, schema="users_api")
    op.alter_column("inventory_movements", "business_date", nullable=False, schema="users_api")
    op.alter_column("cash_movements", "business_date", nullable=False, schema="users_api")

    op.create_index(
        "ix_sales_business_date",
        "sales",
        ["tenant_id", "business_date"],
        schema="users_api",
    )
    op.create_index(
        "ix_obligations_business_date",
        "obligations",
        ["tenant_id", "business_date"],
        schema="users_api",
    )
    op.create_index(
        "ix_inventory_movements_business_date",
        "inventory_movements",
        ["tenant_id", "business_date"],
        schema="users_api",
    )
    op.create_index(
        "ix_cash_movements_business_date",
        "cash_movements",
        ["tenant_id", "business_date"],
        schema="users_api",
    )


def downgrade() -> None:
    op.drop_index("ix_cash_movements_business_date", table_name="cash_movements", schema="users_api")
    op.drop_index(
        "ix_inventory_movements_business_date",
        table_name="inventory_movements",
        schema="users_api",
    )
    op.drop_index("ix_obligations_business_date", table_name="obligations", schema="users_api")
    op.drop_index("ix_sales_business_date", table_name="sales", schema="users_api")
    op.drop_column("cash_movements", "business_date", schema="users_api")
    op.drop_column("inventory_movements", "business_date", schema="users_api")
    op.drop_column("obligations", "business_date", schema="users_api")
    op.drop_column("sales", "business_date", schema="users_api")

"""add cash register traceability to sales, portfolio and inventory

Revision ID: f4c8a1b2d3e4
Revises: e3f5a7c9d1b2
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4c8a1b2d3e4"
down_revision: Union[str, Sequence[str], None] = "e3f5a7c9d1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    for table in (
        "sales",
        "sale_payments",
        "obligations",
        "portfolio_payments",
        "inventory_movements",
    ):
        op.add_column(
            table,
            sa.Column("cash_register_id", sa.Integer(), nullable=True),
            schema=SCHEMA,
        )
        op.create_foreign_key(
            f"fk_{table}_cash_register_id",
            table,
            "cash_registers",
            ["cash_register_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
        )
        op.create_index(
            f"ix_{table}_cash_register",
            table,
            ["tenant_id", "cash_register_id"],
            unique=False,
            schema=SCHEMA,
        )

    # Backfill only when an existing persisted cash movement proves the register.
    op.execute(
        """
        UPDATE users_api.sales sale
        SET cash_register_id = source.cash_register_id
        FROM (
            SELECT DISTINCT ON (tenant_id, origin_id)
                tenant_id,
                origin_id::uuid AS sale_id,
                cash_register_id
            FROM users_api.cash_movements
            WHERE origin_type = 'SALE'
              AND origin_id IS NOT NULL
            ORDER BY tenant_id, origin_id, id
        ) source
        WHERE sale.tenant_id = source.tenant_id
          AND sale.id = source.sale_id
          AND sale.cash_register_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.sale_payments payment
        SET cash_register_id = sale.cash_register_id
        FROM users_api.sales sale
        WHERE payment.tenant_id = sale.tenant_id
          AND payment.sale_id = sale.id
          AND payment.cash_register_id IS NULL
          AND sale.cash_register_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.obligations obligation
        SET cash_register_id = sale.cash_register_id
        FROM users_api.sales sale
        WHERE obligation.tenant_id = sale.tenant_id
          AND obligation.sale_id = sale.id
          AND obligation.cash_register_id IS NULL
          AND sale.cash_register_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.portfolio_payments payment
        SET cash_register_id = movement.cash_register_id
        FROM users_api.cash_movements movement
        WHERE movement.tenant_id = payment.tenant_id
          AND movement.origin_type = 'PORTFOLIO_PAYMENT'
          AND movement.origin_id = payment.id::text
          AND payment.cash_register_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE users_api.inventory_movements movement
        SET cash_register_id = sale.cash_register_id
        FROM users_api.sales sale
        WHERE movement.tenant_id = sale.tenant_id
          AND movement.origin_type = 'SALE'
          AND movement.origin_id = sale.id
          AND movement.cash_register_id IS NULL
          AND sale.cash_register_id IS NOT NULL
        """
    )

    # Existing historical data is preserved. New and updated application flows
    # reject credit as a portfolio payment method.
    op.execute(
        """
        ALTER TABLE users_api.portfolio_payments
        ADD CONSTRAINT ck_portfolio_payments_method_not_credit
        CHECK (UPPER(payment_method) NOT IN ('CREDITO', 'CREDIT', 'CRÉDITO'))
        NOT VALID
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE users_api.portfolio_payments "
        "DROP CONSTRAINT IF EXISTS ck_portfolio_payments_method_not_credit"
    )

    for table in (
        "inventory_movements",
        "portfolio_payments",
        "obligations",
        "sale_payments",
        "sales",
    ):
        op.drop_index(
            f"ix_{table}_cash_register",
            table_name=table,
            schema=SCHEMA,
        )
        op.drop_constraint(
            f"fk_{table}_cash_register_id",
            table,
            type_="foreignkey",
            schema=SCHEMA,
        )
        op.drop_column(table, "cash_register_id", schema=SCHEMA)

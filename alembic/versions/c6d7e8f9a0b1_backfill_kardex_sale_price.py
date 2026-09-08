"""backfill historical sale price data in inventory movements

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
"""

from alembic import op


revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users_api.inventory_movements AS im
        SET profit_percentage =
            (si.unit_price / NULLIF(im.unit_purchase_price, 0)) - 1
        FROM users_api.sale_items AS si
        WHERE im.origin_type = 'SALE'
          AND im.profit_percentage IS NULL
          AND im.origin_id = si.sale_id
          AND im.tenant_id = si.tenant_id
          AND im.product_id = si.product_id
          AND im.unit_purchase_price > 0
          AND si.unit_price IS NOT NULL
        """
    )


def downgrade() -> None:
    # The backfill is intentionally not reverted: profit_percentage is
    # historical audit data and clearing it would destroy information.
    pass

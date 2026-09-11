"""validate portfolio payment method constraint

Revision ID: e4f5a6b7c8d9
Revises: d0e1f2a3b4c5
Create Date: 2026-09-11
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
CONSTRAINT = "ck_portfolio_payments_method_not_credit"


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE {SCHEMA}.portfolio_payments "
        f"VALIDATE CONSTRAINT {CONSTRAINT}"
    )


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE {SCHEMA}.portfolio_payments "
        f"DROP CONSTRAINT IF EXISTS {CONSTRAINT}"
    )
    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.portfolio_payments
        ADD CONSTRAINT {CONSTRAINT}
        CHECK (UPPER(payment_method) NOT IN ('CREDITO', 'CREDIT', 'CRÉDITO'))
        NOT VALID
        """
    )

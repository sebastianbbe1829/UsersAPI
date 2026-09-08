"""drop obsolete portfolio payment status index

Revision ID: d7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
TABLE = "portfolio_payments"
INDEX = "ix_users_api_portfolio_payments_status"


def upgrade() -> None:
    op.drop_index(
        INDEX,
        table_name=TABLE,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.create_index(
        INDEX,
        TABLE,
        ["status"],
        schema=SCHEMA,
    )

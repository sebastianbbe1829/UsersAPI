"""add configured daily base to cash boxes

Revision ID: c4d5e6f7a8b9
Revises: b1c2d3e4f5a6
Create Date: 2026-09-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cash_boxes",
        sa.Column(
            "base_amount",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema="users_api",
    )
    op.create_check_constraint(
        "ck_cash_boxes_base_amount",
        "cash_boxes",
        "base_amount >= 0",
        schema="users_api",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_cash_boxes_base_amount",
        "cash_boxes",
        schema="users_api",
        type_="check",
    )
    op.drop_column("cash_boxes", "base_amount", schema="users_api")

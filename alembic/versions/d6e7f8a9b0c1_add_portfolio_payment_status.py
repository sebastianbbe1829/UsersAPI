"""add portfolio payment status

Revision ID: d6e7f8a9b0c1
Revises: c7d8e9f0a1b2
"""

from alembic import op
import sqlalchemy as sa

revision = "d6e7f8a9b0c1"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None
SCHEMA = "users_api"
TABLE = "portfolio_payments"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'APLICADO'"),
        ),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_portfolio_payments_status",
        TABLE,
        "status IN ('APLICADO', 'ANULADO')",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_portfolio_payments_status",
        TABLE,
        ["status"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_api_portfolio_payments_status",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.drop_constraint(
        "ck_portfolio_payments_status",
        TABLE,
        schema=SCHEMA,
        type_="check",
    )
    op.drop_column(TABLE, "status", schema=SCHEMA)

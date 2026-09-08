"""add client credit limit

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

from alembic import op
import sqlalchemy as sa


revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clients",
        sa.Column(
            "credit_limit",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema="users_api",
    )
    op.create_check_constraint(
        "ck_clients_credit_limit",
        "clients",
        "credit_limit >= 0",
        schema="users_api",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_clients_credit_limit",
        "clients",
        schema="users_api",
        type_="check",
    )
    op.drop_column("clients", "credit_limit", schema="users_api")

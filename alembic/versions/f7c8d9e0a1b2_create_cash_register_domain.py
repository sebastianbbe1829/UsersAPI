"""create cash register domain

Revision ID: f7c8d9e0a1b2
Revises: e3f5a7c9d1b2
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7c8d9e0a1b2"
down_revision: Union[str, Sequence[str], None] = "e3f5a7c9d1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cash_registers",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("opened_by", sa.String(length=100), nullable=False),
        sa.Column("opening_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("closed_by", sa.String(length=100), nullable=True),
        sa.Column("expected_cash", sa.Numeric(18, 2), nullable=True),
        sa.Column("counted_cash", sa.Numeric(18, 2), nullable=True),
        sa.Column("difference", sa.Numeric(18, 2), nullable=True),
        sa.Column("closing_notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["users_api.tenants.id"]),
        sa.CheckConstraint("opening_amount >= 0", name="ck_cash_registers_opening_amount"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_cash_registers_status"),
        schema="users_api",
    )
    op.create_index(
        "ix_cash_registers_tenant_id",
        "cash_registers",
        ["tenant_id"],
        schema="users_api",
    )
    op.create_index(
        "uq_cash_registers_open_tenant",
        "cash_registers",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
        schema="users_api",
    )

    op.create_table(
        "cash_movements",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("cash_register_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("origin_type", sa.String(length=30), nullable=False),
        sa.Column("origin_id", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "cash_register_id"],
            ["users_api.cash_registers.tenant_id", "users_api.cash_registers.id"],
        ),
        sa.CheckConstraint("movement_type IN ('INCOME', 'EXPENSE')", name="ck_cash_movements_type"),
        sa.CheckConstraint("amount > 0", name="ck_cash_movements_amount"),
        schema="users_api",
    )
    op.create_index(
        "ix_cash_movements_tenant_id",
        "cash_movements",
        ["tenant_id"],
        schema="users_api",
    )
    op.create_index(
        "ix_cash_movements_cash_register_id",
        "cash_movements",
        ["cash_register_id"],
        schema="users_api",
    )

    for table, policy in (
        ("cash_registers", "cash_registers_isolation"),
        ("cash_movements", "cash_movements_isolation"),
    ):
        op.execute(f"ALTER TABLE users_api.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {policy}
            ON users_api.{table}
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
            )
            """
        )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS cash_movements_isolation ON users_api.cash_movements")
    op.execute("DROP POLICY IF EXISTS cash_registers_isolation ON users_api.cash_registers")
    op.drop_index("ix_cash_movements_cash_register_id", table_name="cash_movements", schema="users_api")
    op.drop_index("ix_cash_movements_tenant_id", table_name="cash_movements", schema="users_api")
    op.drop_table("cash_movements", schema="users_api")
    op.drop_index("uq_cash_registers_open_tenant", table_name="cash_registers", schema="users_api")
    op.drop_index("ix_cash_registers_tenant_id", table_name="cash_registers", schema="users_api")
    op.drop_table("cash_registers", schema="users_api")

"""create portfolio domain

Revision ID: c7d8e9f0a1b2
Revises: b5c6d7e8f9a0
"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c7d8e9f0a1b2"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None
SCHEMA = "users_api"


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {SCHEMA}.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {SCHEMA}.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY {table}_isolation ON {SCHEMA}.{table}
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)"""
    )


def _disable_rls(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON {SCHEMA}.{table}")
    op.execute(f"ALTER TABLE {SCHEMA}.{table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {SCHEMA}.{table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.create_table(
        "credit_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_limit", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint("approved_limit >= 0", name="ck_credit_limits_approved_limit"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], [f"{SCHEMA}.clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "client_id", name="uq_credit_limits_tenant_client"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_credit_limits_tenant_id", "credit_limits", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_credit_limits_client_id", "credit_limits", ["client_id"], schema=SCHEMA)

    op.create_table(
        "obligations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initial_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint("initial_amount > 0", name="ck_obligations_initial_amount"),
        sa.CheckConstraint("balance >= 0 AND balance <= initial_amount", name="ck_obligations_balance"),
        sa.CheckConstraint("status IN ('ACTIVE', 'SETTLED', 'CANCELLED')", name="ck_obligations_status"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], [f"{SCHEMA}.clients.id"]),
        sa.ForeignKeyConstraint(["sale_id"], [f"{SCHEMA}.sales.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "sale_id", name="uq_obligations_tenant_sale"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_obligations_tenant_id", "obligations", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_obligations_client_id", "obligations", ["client_id"], schema=SCHEMA)
    op.create_index("ix_users_api_obligations_sale_id", "obligations", ["sale_id"], schema=SCHEMA)

    op.create_table(
        "portfolio_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_portfolio_payments_amount"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], [f"{SCHEMA}.clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_portfolio_payments_tenant_id", "portfolio_payments", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_portfolio_payments_client_id", "portfolio_payments", ["client_id"], schema=SCHEMA)

    op.create_table(
        "payment_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("obligation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_allocations_amount"),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["payment_id"], [f"{SCHEMA}.portfolio_payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obligation_id"], [f"{SCHEMA}.obligations.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_payment_allocations_tenant_id", "payment_allocations", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_payment_allocations_payment_id", "payment_allocations", ["payment_id"], schema=SCHEMA)
    op.create_index("ix_users_api_payment_allocations_obligation_id", "payment_allocations", ["obligation_id"], schema=SCHEMA)

    bind = op.get_bind()
    clients = bind.execute(
        sa.text(f"SELECT id, tenant_id, credit_limit, created_by FROM {SCHEMA}.clients")
    ).mappings().all()
    for client in clients:
        bind.execute(
            sa.text(
                f"""INSERT INTO {SCHEMA}.credit_limits
                (id, tenant_id, client_id, approved_limit, active, created_by)
                VALUES (:id, :tenant_id, :client_id, :approved_limit, true, :created_by)"""
            ),
            {
                "id": uuid.uuid4(),
                "tenant_id": client["tenant_id"],
                "client_id": client["id"],
                "approved_limit": client["credit_limit"],
                "created_by": client["created_by"],
            },
        )
    op.drop_constraint("ck_clients_credit_limit", "clients", schema=SCHEMA, type_="check")
    op.drop_column("clients", "credit_limit", schema=SCHEMA)

    for table in ("credit_limits", "obligations", "portfolio_payments", "payment_allocations"):
        _enable_rls(table)


def downgrade() -> None:
    for table in ("credit_limits", "obligations", "portfolio_payments", "payment_allocations"):
        _disable_rls(table)

    op.add_column(
        "clients",
        sa.Column("credit_limit", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        schema=SCHEMA,
    )
    op.execute(
        f"""UPDATE {SCHEMA}.clients c
        SET credit_limit = COALESCE((
            SELECT cl.approved_limit
            FROM {SCHEMA}.credit_limits cl
            WHERE cl.tenant_id = c.tenant_id AND cl.client_id = c.id
        ), 0)"""
    )
    op.create_check_constraint("ck_clients_credit_limit", "clients", "credit_limit >= 0", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_payment_allocations_obligation_id", "payment_allocations"),
        ("ix_users_api_payment_allocations_payment_id", "payment_allocations"),
        ("ix_users_api_payment_allocations_tenant_id", "payment_allocations"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("payment_allocations", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_portfolio_payments_client_id", "portfolio_payments"),
        ("ix_users_api_portfolio_payments_tenant_id", "portfolio_payments"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("portfolio_payments", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_obligations_sale_id", "obligations"),
        ("ix_users_api_obligations_client_id", "obligations"),
        ("ix_users_api_obligations_tenant_id", "obligations"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("obligations", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_credit_limits_client_id", "credit_limits"),
        ("ix_users_api_credit_limits_tenant_id", "credit_limits"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("credit_limits", schema=SCHEMA)

"""add cash operating day lifecycle

Revision ID: b1c2d3e4f5a6
Revises: ed6fe9b433af
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "ed6fe9b433af"
branch_labels = None
depends_on = None


CASH_DAY_PERMISSIONS = (
    (
        "CASH_DAY_START",
        "Iniciar día de caja",
        "Permite iniciar el día operativo y abrir todas las sucursales y cajas activas",
    ),
    (
        "CASH_BRANCH_CLOSE",
        "Cerrar sucursal",
        "Permite cerrar una sucursal cuando todas sus cajas están cerradas",
    ),
    (
        "CASH_DAY_CLOSE",
        "Cerrar día de caja",
        "Permite cerrar el día cuando todas las sucursales están cerradas",
    ),
)


def upgrade() -> None:
    op.create_table(
        "cash_days",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("opened_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("opened_by", sa.String(100), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("closed_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["users_api.tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_cash_days_tenant_id"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_cash_days_status"),
        schema="users_api",
    )
    op.create_index("uq_cash_days_tenant_date", "cash_days", ["tenant_id", "business_date"], unique=True, schema="users_api")
    op.create_index("uq_cash_days_open_tenant", "cash_days", ["tenant_id"], unique=True, postgresql_where=sa.text("status = 'OPEN'"), schema="users_api")
    op.create_index("ix_cash_days_tenant_id", "cash_days", ["tenant_id"], schema="users_api")

    op.create_table(
        "cash_day_branches",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("cash_day_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("opened_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("opened_by", sa.String(100), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("closed_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id", "cash_day_id"], ["users_api.cash_days.tenant_id", "users_api.cash_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "branch_id"], ["users_api.branches.tenant_id", "users_api.branches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "cash_day_id", "branch_id", name="uq_cash_day_branches_day_branch"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_cash_day_branches_status"),
        schema="users_api",
    )
    op.create_index("ix_cash_day_branches_tenant_id", "cash_day_branches", ["tenant_id"], schema="users_api")
    op.create_index("ix_cash_day_branches_cash_day_id", "cash_day_branches", ["cash_day_id"], schema="users_api")

    op.add_column("cash_registers", sa.Column("cash_day_id", sa.Integer(), nullable=True), schema="users_api")
    op.create_foreign_key(
        "fk_cash_registers_cash_day",
        "cash_registers",
        "cash_days",
        ["tenant_id", "cash_day_id"],
        ["tenant_id", "id"],
        source_schema="users_api",
        referent_schema="users_api",
    )
    op.create_index("ix_cash_registers_cash_day_id", "cash_registers", ["cash_day_id"], schema="users_api")

    for table, policy in (("cash_days", "cash_days_isolation"), ("cash_day_branches", "cash_day_branches_isolation")):
        op.execute(f"ALTER TABLE users_api.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {policy} ON users_api.{table} "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)"
        )

    for code, name, description in CASH_DAY_PERMISSIONS:
        op.execute(
            sa.text(
                """
                INSERT INTO users_api.permissions (code, name, description, status, created_by)
                VALUES (:code, :name, :description, 1, 'SYSTEM')
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(code=code, name=name, description=description)
        )

    op.execute(
        sa.text(
            """
            INSERT INTO users_api.role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM users_api.roles r
            CROSS JOIN users_api.permissions p
            WHERE r.code = 'ADMIN'
              AND p.code IN ('CASH_DAY_START', 'CASH_BRANCH_CLOSE', 'CASH_DAY_CLOSE')
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM users_api.role_permissions rp
        USING users_api.permissions p
        WHERE rp.permission_id = p.id
          AND p.code IN ('CASH_DAY_START', 'CASH_BRANCH_CLOSE', 'CASH_DAY_CLOSE')
        """
    )
    op.execute("DELETE FROM users_api.permissions WHERE code IN ('CASH_DAY_START', 'CASH_BRANCH_CLOSE', 'CASH_DAY_CLOSE')")
    op.execute("DROP POLICY IF EXISTS cash_day_branches_isolation ON users_api.cash_day_branches")
    op.execute("DROP POLICY IF EXISTS cash_days_isolation ON users_api.cash_days")
    op.drop_index("ix_cash_registers_cash_day_id", table_name="cash_registers", schema="users_api")
    op.drop_constraint("fk_cash_registers_cash_day", "cash_registers", schema="users_api", type_="foreignkey")
    op.drop_column("cash_registers", "cash_day_id", schema="users_api")
    op.drop_index("ix_cash_day_branches_cash_day_id", table_name="cash_day_branches", schema="users_api")
    op.drop_index("ix_cash_day_branches_tenant_id", table_name="cash_day_branches", schema="users_api")
    op.drop_table("cash_day_branches", schema="users_api")
    op.drop_index("ix_cash_days_tenant_id", table_name="cash_days", schema="users_api")
    op.drop_index("uq_cash_days_open_tenant", table_name="cash_days", schema="users_api")
    op.drop_index("uq_cash_days_tenant_date", table_name="cash_days", schema="users_api")
    op.drop_table("cash_days", schema="users_api")

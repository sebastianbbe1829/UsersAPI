"""create extinguisher MVP tables

Revision ID: d4e7f1a2b903
Revises: c8f2a4d7b901
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e7f1a2b903"
down_revision: Union[str, Sequence[str], None] = "c8f2a4d7b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA = "users_api"

EXTINGUISHERS = "extinguishers"
INSPECTIONS = "extinguisher_inspections"
INSPECTION_ITEMS = "extinguisher_inspection_items"
RECHARGES = "extinguisher_recharges"


POLICY_EXTINGUISHERS = "extinguishers_isolation"
POLICY_INSPECTIONS = "extinguisher_inspections_isolation"
POLICY_INSPECTION_ITEMS = "extinguisher_inspection_items_isolation"
POLICY_RECHARGES = "extinguisher_recharges_isolation"


def _enable_rls(table_name: str) -> None:
    op.execute(
        f"ALTER TABLE {SCHEMA}.{table_name} ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        f"ALTER TABLE {SCHEMA}.{table_name} FORCE ROW LEVEL SECURITY"
    )


def upgrade() -> None:

    # ========================================================
    # EXTINTORES
    # ========================================================
    op.create_table(
        EXTINGUISHERS,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("extinguisher_type", sa.String(length=50), nullable=False),
        sa.Column("capacity", sa.String(length=30), nullable=True),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("last_recharge_date", sa.Date(), nullable=True),
        sa.Column("next_recharge_date", sa.Date(), nullable=True),
        sa.Column("last_hydrostatic_test_date", sa.Date(), nullable=True),
        sa.Column("next_hydrostatic_test_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column(
            "is_stock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_extinguishers_tenant_code",
        ),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_users_api_extinguishers_tenant_id",
        EXTINGUISHERS,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguishers_code",
        EXTINGUISHERS,
        ["code"],
        unique=False,
        schema=SCHEMA,
    )

    # ========================================================
    # INSPECCIONES
    # ========================================================
    op.create_table(
        INSPECTIONS,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("extinguisher_id", sa.Integer(), nullable=False),
        sa.Column("inspection_date", sa.Date(), nullable=False),
        sa.Column("inspector_user_id", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extinguisher_id"],
            [f"{SCHEMA}.{EXTINGUISHERS}.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inspector_user_id"],
            [f"{SCHEMA}.user_tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_users_api_extinguisher_inspections_tenant_id",
        INSPECTIONS,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguisher_inspections_extinguisher_id",
        INSPECTIONS,
        ["extinguisher_id"],
        unique=False,
        schema=SCHEMA,
    )

    # ========================================================
    # ITEMS DE INSPECCIÓN
    # ========================================================
    op.create_table(
        INSPECTION_ITEMS,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("inspection_id", sa.Integer(), nullable=False),
        sa.Column("item", sa.String(length=50), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            [f"{SCHEMA}.{INSPECTIONS}.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_users_api_extinguisher_inspection_items_inspection_id",
        INSPECTION_ITEMS,
        ["inspection_id"],
        unique=False,
        schema=SCHEMA,
    )

    # ========================================================
    # RECARGAS
    # ========================================================
    op.create_table(
        RECHARGES,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("extinguisher_id", sa.Integer(), nullable=False),
        sa.Column("recharge_date", sa.Date(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extinguisher_id"],
            [f"{SCHEMA}.{EXTINGUISHERS}.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.user_tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_users_api_extinguisher_recharges_tenant_id",
        RECHARGES,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguisher_recharges_extinguisher_id",
        RECHARGES,
        ["extinguisher_id"],
        unique=False,
        schema=SCHEMA,
    )

    # ========================================================
    # ROW LEVEL SECURITY
    # ========================================================
    for table_name in (
        EXTINGUISHERS,
        INSPECTIONS,
        INSPECTION_ITEMS,
        RECHARGES,
    ):
        _enable_rls(table_name)

    op.execute(
        f"""
        CREATE POLICY {POLICY_EXTINGUISHERS}
        ON {SCHEMA}.{EXTINGUISHERS}
        USING (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        """
    )

    op.execute(
        f"""
        CREATE POLICY {POLICY_INSPECTIONS}
        ON {SCHEMA}.{INSPECTIONS}
        USING (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        """
    )

    op.execute(
        f"""
        CREATE POLICY {POLICY_INSPECTION_ITEMS}
        ON {SCHEMA}.{INSPECTION_ITEMS}
        USING (
            EXISTS (
                SELECT 1
                FROM {SCHEMA}.{INSPECTIONS} i
                WHERE i.id = inspection_id
                  AND i.tenant_id = NULLIF(
                      current_setting('app.current_tenant_id', true),
                      ''
                  )::integer
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM {SCHEMA}.{INSPECTIONS} i
                WHERE i.id = inspection_id
                  AND i.tenant_id = NULLIF(
                      current_setting('app.current_tenant_id', true),
                      ''
                  )::integer
            )
        )
        """
    )

    op.execute(
        f"""
        CREATE POLICY {POLICY_RECHARGES}
        ON {SCHEMA}.{RECHARGES}
        USING (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        """
    )


def downgrade() -> None:

    for policy_name, table_name in (
        (POLICY_INSPECTION_ITEMS, INSPECTION_ITEMS),
        (POLICY_RECHARGES, RECHARGES),
        (POLICY_INSPECTIONS, INSPECTIONS),
        (POLICY_EXTINGUISHERS, EXTINGUISHERS),
    ):
        op.execute(
            f"DROP POLICY IF EXISTS {policy_name} ON {SCHEMA}.{table_name}"
        )
        op.execute(
            f"ALTER TABLE {SCHEMA}.{table_name} NO FORCE ROW LEVEL SECURITY"
        )
        op.execute(
            f"ALTER TABLE {SCHEMA}.{table_name} DISABLE ROW LEVEL SECURITY"
        )

    op.drop_index(
        "ix_users_api_extinguisher_recharges_extinguisher_id",
        table_name=RECHARGES,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_extinguisher_recharges_tenant_id",
        table_name=RECHARGES,
        schema=SCHEMA,
    )
    op.drop_table(RECHARGES, schema=SCHEMA)

    op.drop_index(
        "ix_users_api_extinguisher_inspection_items_inspection_id",
        table_name=INSPECTION_ITEMS,
        schema=SCHEMA,
    )
    op.drop_table(INSPECTION_ITEMS, schema=SCHEMA)

    op.drop_index(
        "ix_users_api_extinguisher_inspections_extinguisher_id",
        table_name=INSPECTIONS,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_extinguisher_inspections_tenant_id",
        table_name=INSPECTIONS,
        schema=SCHEMA,
    )
    op.drop_table(INSPECTIONS, schema=SCHEMA)

    op.drop_index(
        "ix_users_api_extinguishers_code",
        table_name=EXTINGUISHERS,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_extinguishers_tenant_id",
        table_name=EXTINGUISHERS,
        schema=SCHEMA,
    )
    op.drop_table(EXTINGUISHERS, schema=SCHEMA)

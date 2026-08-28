"""create tenant UI configuration table

Revision ID: c8f2a4d7b901
Revises: 7b2e4f6a91c3
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8f2a4d7b901"
down_revision: Union[str, Sequence[str], None] = "7b2e4f6a91c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "tenant_configs"
SCHEMA = "users_api"
POLICY_NAME = "tenant_configs_isolation"


def upgrade() -> None:

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("app_title", sa.String(length=150), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column(
            "primary_color",
            sa.String(length=7),
            nullable=False,
            server_default=sa.text("'#0D6EFD'"),
        ),
        sa.Column(
            "secondary_color",
            sa.String(length=7),
            nullable=False,
            server_default=sa.text("'#6C757D'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_configs_tenant_id"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_users_api_tenant_configs_tenant_id",
        TABLE_NAME,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.{TABLE_NAME}
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.{TABLE_NAME}
        FORCE ROW LEVEL SECURITY
        """
    )

    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME}
        ON {SCHEMA}.{TABLE_NAME}
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

    op.execute(
        f"""
        DROP POLICY IF EXISTS {POLICY_NAME}
        ON {SCHEMA}.{TABLE_NAME}
        """
    )

    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.{TABLE_NAME}
        NO FORCE ROW LEVEL SECURITY
        """
    )

    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.{TABLE_NAME}
        DISABLE ROW LEVEL SECURITY
        """
    )

    op.drop_index(
        "ix_users_api_tenant_configs_tenant_id",
        table_name=TABLE_NAME,
        schema=SCHEMA,
    )

    op.drop_table(TABLE_NAME, schema=SCHEMA)

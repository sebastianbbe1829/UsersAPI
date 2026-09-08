"""add rls policies to portfolio tables

Revision ID: e1a2b3c4d5e6
Revises: d7f8a9b0c1d2
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d7f8a9b0c1d2"
branch_labels = None
depends_on = None

SCHEMA = "users_api"


POLICY_SQL = {
    "credit_limits": """
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
    """,
    "obligations": """
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
    """,
    "portfolio_payments": """
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
    """,
    "payment_allocations": """
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
    """,
}

TABLES = (
    "credit_limits",
    "obligations",
    "portfolio_payments",
    "payment_allocations",
)


def upgrade() -> None:
    for table_name in TABLES:
        op.execute(
            f"""
            ALTER TABLE {SCHEMA}.{table_name}
            ENABLE ROW LEVEL SECURITY
            """
        )
        op.execute(
            f"""
            ALTER TABLE {SCHEMA}.{table_name}
            FORCE ROW LEVEL SECURITY
            """
        )

        policy_expression = POLICY_SQL[table_name]
        op.execute(
            f"""
            CREATE POLICY {table_name}_tenant_isolation
            ON {SCHEMA}.{table_name}
            USING ({policy_expression})
            WITH CHECK ({policy_expression})
            """
        )


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.execute(
            f"""
            DROP POLICY IF EXISTS {table_name}_tenant_isolation
            ON {SCHEMA}.{table_name}
            """
        )
        op.execute(
            f"""
            ALTER TABLE {SCHEMA}.{table_name}
            NO FORCE ROW LEVEL SECURITY
            """
        )
        op.execute(
            f"""
            ALTER TABLE {SCHEMA}.{table_name}
            DISABLE ROW LEVEL SECURITY
            """
        )

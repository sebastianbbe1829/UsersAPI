"""cleanup tenants rls policies

Revision ID: a44c1eed7f2e
Revises: 0d04a013631d
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a44c1eed7f2e"
down_revision: Union[str, Sequence[str], None] = "0d04a013631d"

branch_labels = None
depends_on = None


def upgrade() -> None:

    # --------------------------------------------------------
    # Limpiar políticas anteriores
    # --------------------------------------------------------

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_isolation
        ON users_api.tenants
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_select_isolation
        ON users_api.tenants
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_update_isolation
        ON users_api.tenants
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_select_update_isolation
        ON users_api.tenants
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_insert_bootstrap
        ON users_api.tenants
        """
    )


    # --------------------------------------------------------
    # Política SELECT / UPDATE normal multi tenant
    # --------------------------------------------------------

    op.execute(
        """
        CREATE POLICY tenants_select_isolation
        ON users_api.tenants
        FOR SELECT
        USING (
            id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        """
    )


    op.execute(
        """
        CREATE POLICY tenants_update_isolation
        ON users_api.tenants
        FOR UPDATE
        USING (
            id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        WITH CHECK (
            id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        """
    )


    # --------------------------------------------------------
    # Bootstrap inicial
    # --------------------------------------------------------

    op.execute(
        """
        CREATE POLICY tenants_insert_bootstrap
        ON users_api.tenants
        FOR INSERT
        WITH CHECK (true)
        """
    )


def downgrade() -> None:

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_insert_bootstrap
        ON users_api.tenants
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_update_isolation
        ON users_api.tenants
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_select_isolation
        ON users_api.tenants
        """
    )
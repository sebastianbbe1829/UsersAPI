"""
allow tenant bootstrap insert

Revision ID: 0d04a013631d
Revises: 5509b9f8cf05
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0d04a013631d"
down_revision: Union[str, Sequence[str], None] = "5509b9f8cf05"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ========================================================
    # TENANTS
    #
    # El tenant es especial:
    # - Durante bootstrap todavía no existe tenant_id.
    # - Permitimos INSERT solamente.
    # - SELECT/UPDATE siguen aislados por tenant.
    # ========================================================

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_isolation
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
        DO $$
        BEGIN

            IF NOT EXISTS (
                SELECT 1
                FROM pg_policies
                WHERE schemaname = 'users_api'
                AND tablename = 'tenants'
                AND policyname = 'tenants_select_update_isolation'
            ) THEN

                CREATE POLICY tenants_select_update_isolation
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
                );

            END IF;

        END
        $$;
        """
    )


    op.execute(
        """
        DO $$
        BEGIN

            IF NOT EXISTS (
                SELECT 1
                FROM pg_policies
                WHERE schemaname = 'users_api'
                AND tablename = 'tenants'
                AND policyname = 'tenants_insert_bootstrap'
            ) THEN

                CREATE POLICY tenants_insert_bootstrap
                ON users_api.tenants
                FOR INSERT
                WITH CHECK (true);

            END IF;

        END
        $$;
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
        DROP POLICY IF EXISTS tenants_select_update_isolation
        ON users_api.tenants
        """
    )


    op.execute(
        """
        CREATE POLICY tenants_isolation
        ON users_api.tenants
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
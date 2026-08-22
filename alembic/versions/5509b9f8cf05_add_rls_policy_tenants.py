"""add rls tenant policies

Revision ID: 5509b9f8cf05
Revises: f1bd492c4eed
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "5509b9f8cf05"
down_revision: Union[str, Sequence[str], None] = "f1bd492c4eed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ========================================================
    # USER_TENANTS
    # ========================================================

    op.execute(
        """
        CREATE POLICY user_tenants_isolation
        ON users_api.user_tenants
        USING (
            tenant_id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        """
    )

    # ========================================================
    # ROLES
    # ========================================================

    op.execute(
        """
        CREATE POLICY roles_isolation
        ON users_api.roles
        USING (
            tenant_id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting(
                    'app.current_tenant_id',
                    true
                ),
                ''
            )::integer
        )
        """
    )

    # ========================================================
    # USER_TENANT_ROLES
    #
    # La tabla no tiene tenant_id.
    # El tenant se obtiene desde user_tenants.
    # ========================================================

    op.execute(
        """
        CREATE POLICY user_tenant_roles_isolation
        ON users_api.user_tenant_roles
        USING (
            EXISTS (
                SELECT 1
                FROM users_api.user_tenants ut
                WHERE ut.id = user_tenant_id
                  AND ut.tenant_id = NULLIF(
                      current_setting(
                          'app.current_tenant_id',
                          true
                      ),
                      ''
                  )::integer
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM users_api.user_tenants ut
                WHERE ut.id = user_tenant_id
                  AND ut.tenant_id = NULLIF(
                      current_setting(
                          'app.current_tenant_id',
                          true
                      ),
                      ''
                  )::integer
            )
        )
        """
    )

    # ========================================================
    # ROLE_PERMISSIONS
    #
    # La tabla no tiene tenant_id.
    # El tenant se obtiene desde roles.
    # ========================================================

    op.execute(
        """
        CREATE POLICY role_permissions_isolation
        ON users_api.role_permissions
        USING (
            EXISTS (
                SELECT 1
                FROM users_api.roles r
                WHERE r.id = role_id
                  AND r.tenant_id = NULLIF(
                      current_setting(
                          'app.current_tenant_id',
                          true
                      ),
                      ''
                  )::integer
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM users_api.roles r
                WHERE r.id = role_id
                  AND r.tenant_id = NULLIF(
                      current_setting(
                          'app.current_tenant_id',
                          true
                      ),
                      ''
                  )::integer
            )
        )
        """
    )


def downgrade() -> None:

    op.execute(
        """
        DROP POLICY IF EXISTS role_permissions_isolation
        ON users_api.role_permissions
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS user_tenant_roles_isolation
        ON users_api.user_tenant_roles
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS roles_isolation
        ON users_api.roles
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS user_tenants_isolation
        ON users_api.user_tenants
        """
    )
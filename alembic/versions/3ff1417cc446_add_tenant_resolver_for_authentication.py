"""add tenant resolver for authentication

Revision ID: 3ff1417cc446
Revises: e020ccb4c0c0
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "3ff1417cc446"

down_revision: Union[str, Sequence[str], None] = "e020ccb4c0c0"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea una función SECURITY DEFINER para resolver el tenant
    a partir de su slug durante el proceso de autenticación.

    La función devuelve únicamente el ID del tenant.
    No modifica ni elimina las políticas RLS.
    """

    op.execute(
        """
        CREATE OR REPLACE FUNCTION users_api.resolve_tenant_id(
            p_tenant_slug text
        )
        RETURNS integer
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = users_api, pg_catalog
        AS $$
            SELECT id
            FROM users_api.tenants
            WHERE slug = p_tenant_slug
              AND status = 1
            LIMIT 1
        $$;
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION users_api.resolve_tenant_id(text)
        FROM PUBLIC;
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION users_api.resolve_tenant_id(text)
        TO users_api_app;
        """
    )


def downgrade() -> None:
    """
    Elimina la función de resolución de tenant.
    """

    op.execute(
        """
        REVOKE EXECUTE
        ON FUNCTION users_api.resolve_tenant_id(text)
        FROM users_api_app;
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS users_api.resolve_tenant_id(text);
        """
    )
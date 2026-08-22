"""add activation token tenant resolver

Revision ID: 01b9e3e9e8f2
Revises: 3ff1417cc446
Create Date: 2026-08-22 14:57:04.835569

"""

from typing import Sequence, Union

from alembic import op


# ============================================================
# REVISION
# ============================================================

revision: str = "01b9e3e9e8f2"

down_revision: Union[str, Sequence[str], None] = "3ff1417cc446"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade() -> None:

    op.execute(
        """
        CREATE OR REPLACE FUNCTION
            users_api.resolve_tenant_id_by_activation_token(
                p_activation_token text
            )
        RETURNS integer
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path TO 'users_api', 'pg_catalog'
        AS $function$

            SELECT tenant_id
            FROM users_api.user_tenants
            WHERE activation_token = p_activation_token
            LIMIT 1

        $function$;
        """
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade() -> None:

    op.execute(
        """
        DROP FUNCTION IF EXISTS
            users_api.resolve_tenant_id_by_activation_token(text);
        """
    )
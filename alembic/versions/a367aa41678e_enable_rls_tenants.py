"""enable rls tenants

Revision ID: a367aa41678e
Revises: f0ffaafa9330
Create Date: 2026-08-22 12:31:16.490571

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a367aa41678e"
down_revision: Union[str, Sequence[str], None] = "f0ffaafa9330"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================================
    # RLS - TENANTS
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.tenants
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.tenants
        FORCE ROW LEVEL SECURITY
        """
    )

    # --------------------------------------------------------
    # Eliminar policy si existiera
    # --------------------------------------------------------

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_isolation
        ON users_api.tenants
        """
    )

    # --------------------------------------------------------
    # Policy de aislamiento por tenant
    # --------------------------------------------------------

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


def downgrade() -> None:
    # ========================================================
    # RLS - TENANTS
    # ========================================================

    op.execute(
        """
        DROP POLICY IF EXISTS tenants_isolation
        ON users_api.tenants
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.tenants
        DISABLE ROW LEVEL SECURITY
        """
    )

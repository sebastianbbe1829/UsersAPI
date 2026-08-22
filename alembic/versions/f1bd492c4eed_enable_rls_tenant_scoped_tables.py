"""enable rls tenant scoped tables

Revision ID: f1bd492c4eed
Revises: a367aa41678e
Create Date: 2026-08-22 12:35:24.604982

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f1bd492c4eed"
down_revision: Union[str, Sequence[str], None] = "a367aa41678e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ========================================================
    # USER_TENANTS
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.user_tenants
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.user_tenants
        FORCE ROW LEVEL SECURITY
        """
    )

    # ========================================================
    # USER_TENANT_ROLES
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.user_tenant_roles
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.user_tenant_roles
        FORCE ROW LEVEL SECURITY
        """
    )

    # ========================================================
    # ROLES
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.roles
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.roles
        FORCE ROW LEVEL SECURITY
        """
    )

    # ========================================================
    # ROLE_PERMISSIONS
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.role_permissions
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.role_permissions
        FORCE ROW LEVEL SECURITY
        """
    )


def downgrade() -> None:

    # ========================================================
    # ROLE_PERMISSIONS
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.role_permissions
        NO FORCE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.role_permissions
        DISABLE ROW LEVEL SECURITY
        """
    )

    # ========================================================
    # ROLES
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.roles
        NO FORCE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.roles
        DISABLE ROW LEVEL SECURITY
        """
    )

    # ========================================================
    # USER_TENANT_ROLES
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.user_tenant_roles
        NO FORCE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.user_tenant_roles
        DISABLE ROW LEVEL SECURITY
        """
    )

    # ========================================================
    # USER_TENANTS
    # ========================================================

    op.execute(
        """
        ALTER TABLE users_api.user_tenants
        NO FORCE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE users_api.user_tenants
        DISABLE ROW LEVEL SECURITY
        """
    )
"""disable force rls for tenant bootstrap

Revision ID: 5a9dd5c6b016
Revises: 0d04a013631d
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op


revision: str = "5a9dd5c6b016"
down_revision: Union[str, Sequence[str], None] = "0d04a013631d"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.execute(
        """
        ALTER TABLE users_api.tenants
        NO FORCE ROW LEVEL SECURITY
        """
    )


def downgrade() -> None:

    op.execute(
        """
        ALTER TABLE users_api.tenants
        FORCE ROW LEVEL SECURITY
        """
    )
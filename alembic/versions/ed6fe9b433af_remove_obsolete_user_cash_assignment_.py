"""remove obsolete user cash assignment unique constraint

Revision ID: ed6fe9b433af
Revises: a2b3c4d5e6f7
Create Date: 2026-09-10 00:07:50.254320

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ed6fe9b433af'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE users_api.user_cash_assignments "
        "DROP CONSTRAINT IF EXISTS uq_user_cash_assignments_tenant_id"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint(
        op.f('uq_user_cash_assignments_tenant_id'),
        'user_cash_assignments',
        ['tenant_id', 'id'],
        schema='users_api',
        postgresql_nulls_not_distinct=False,
    )

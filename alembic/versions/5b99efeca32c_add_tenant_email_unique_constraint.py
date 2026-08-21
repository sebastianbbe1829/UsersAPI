"""add tenant email unique constraint

Revision ID: 5b99efeca32c
Revises: b7c2d9e4f1a6
Create Date: 2026-08-20 19:06:49.749846

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5b99efeca32c"
down_revision: Union[str, Sequence[str], None] = "b7c2d9e4f1a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_unique_constraint(
        "uq_user_tenants_tenant_email",
        "user_tenants",
        ["tenant_id", "email"],
        schema="users_api",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "uq_user_tenants_tenant_email",
        "user_tenants",
        schema="users_api",
        type_="unique",
    )
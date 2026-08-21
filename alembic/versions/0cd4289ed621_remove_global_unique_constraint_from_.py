"""remove global unique constraint from user dni

Revision ID: 0cd4289ed621
Revises: 5b99efeca32c
Create Date: 2026-08-20 19:21:26.745286

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0cd4289ed621"
down_revision: Union[str, Sequence[str], None] = "5b99efeca32c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_index(
        "ix_users_api_app_users_dni",
        table_name="app_users",
        schema="users_api",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.create_index(
        "ix_users_api_app_users_dni",
        "app_users",
        ["dni"],
        unique=True,
        schema="users_api",
    )
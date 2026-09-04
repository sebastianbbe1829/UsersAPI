"""align global user DNI indexes with model

Revision ID: 9e7f6a1b2c34
Revises: 8c2d3e4f5a61
"""

from typing import Sequence, Union

from alembic import op


revision: str = "9e7f6a1b2c34"
down_revision: Union[str, Sequence[str], None] = "8c2d3e4f5a61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    """Align global_users DNI indexes with the SQLAlchemy model."""
    op.execute(
        "DROP INDEX IF EXISTS users_api.ix_users_api_global_users_dni"
    )
    op.execute(
        "DROP INDEX IF EXISTS users_api.ix_users_api_global_users_name"
    )
    op.execute(
        "DROP INDEX IF EXISTS users_api.uq_global_users_dni"
    )
    op.create_index(
        "uq_global_users_dni",
        "global_users",
        ["dni"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Restore the previous non-unique DNI/name indexes."""
    op.execute(
        "DROP INDEX IF EXISTS users_api.uq_global_users_dni"
    )
    op.create_index(
        "ix_users_api_global_users_dni",
        "global_users",
        ["dni"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_global_users_name",
        "global_users",
        ["name"],
        unique=False,
        schema=SCHEMA,
    )

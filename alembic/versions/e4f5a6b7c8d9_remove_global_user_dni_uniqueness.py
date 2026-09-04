"""remove global uniqueness from user DNI

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
TABLE = "global_users"


def upgrade() -> None:
    # DNI is not globally unique: the same DNI may belong to users
    # associated with different tenants.
    op.drop_index(
        "uq_global_users_dni",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_global_users_dni",
        TABLE,
        ["dni"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_global_users_name",
        TABLE,
        ["name"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_api_global_users_name",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_global_users_dni",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.create_index(
        "uq_global_users_dni",
        TABLE,
        ["dni"],
        unique=True,
        schema=SCHEMA,
    )

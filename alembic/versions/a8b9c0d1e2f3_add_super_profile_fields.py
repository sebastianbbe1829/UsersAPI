"""add SUPER profile fields to global users

Revision ID: a8b9c0d1e2f3
Revises: c3f8a1d6b204, 7b2e4f6a91c3
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = (
    "c3f8a1d6b204",
    "7b2e4f6a91c3",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    # These profile columns are also reconciled by migration c1d2e3f4a5b6,
    # which is already an ancestor of this merge path. Keep this migration
    # safe for both fresh databases and databases upgraded through c1d2e3f4a5b6.
    op.execute(
        """
        ALTER TABLE users_api.global_users
        ADD COLUMN IF NOT EXISTS dni varchar(20),
        ADD COLUMN IF NOT EXISTS name varchar(100),
        ADD COLUMN IF NOT EXISTS phone varchar(30)
        """
    )

    # The current model intentionally allows repeated DNI values and exposes
    # a normal (non-unique) index. Do not recreate the historical unique DNI
    # index here because c1d2e3f4a5b6 removes that constraint.
    op.execute(
        """
        DROP INDEX IF EXISTS users_api.uq_global_users_dni;
        CREATE INDEX IF NOT EXISTS ix_users_api_global_users_dni
        ON users_api.global_users (dni);
        CREATE INDEX IF NOT EXISTS ix_users_api.global_users_name
        ON users_api.global_users (name);
        """
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE
        ON TABLE users_api.global_users
        TO users_api_app;
        """
    )


def downgrade() -> None:
    # The profile columns are owned by the reconciliation migration in the
    # current migration graph, so this merge migration must not remove them.
    pass

"""add SUPER profile fields to global users

Revision ID: a8b9c0d1e2f3
Revises: c3f8a1d6b204, 7b2e4f6a91c3
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = (
    "c3f8a1d6b204",
    "7b2e4f6a91c3",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column(
        "global_users",
        sa.Column("dni", sa.String(length=20), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "global_users",
        sa.Column("name", sa.String(length=100), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "global_users",
        sa.Column("phone", sa.String(length=30), nullable=True),
        schema=SCHEMA,
    )

    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_global_users_dni
            ON users_api.global_users (dni)
            WHERE dni IS NOT NULL
            """
        )
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE
        ON TABLE users_api.global_users
        TO users_api_app;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS users_api.uq_global_users_dni")
    op.drop_column("global_users", "phone", schema=SCHEMA)
    op.drop_column("global_users", "name", schema=SCHEMA)
    op.drop_column("global_users", "dni", schema=SCHEMA)

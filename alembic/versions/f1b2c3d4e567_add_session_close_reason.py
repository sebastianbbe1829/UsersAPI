"""add session close reason

Revision ID: f1b2c3d4e567
Revises: e6a7b8c9d012
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1b2c3d4e567"
down_revision: Union[str, Sequence[str], None] = "e6a7b8c9d012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("close_reason", sa.String(length=30), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("auth_sessions", "close_reason", schema=SCHEMA)

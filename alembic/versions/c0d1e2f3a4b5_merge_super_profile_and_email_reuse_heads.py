"""merge SUPER profile and tenant email reuse migration heads

Revision ID: c0d1e2f3a4b5
Revises: a8b9c0d1e2f3, b9c0d1e2f3a4
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = (
    "a8b9c0d1e2f3",
    "b9c0d1e2f3a4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

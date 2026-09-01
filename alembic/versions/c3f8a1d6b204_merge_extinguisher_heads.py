"""merge extinguisher migration heads

Revision ID: c3f8a1d6b204
Revises: f7a9c2e1b304, b4c6d8e2f901
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c3f8a1d6b204"
down_revision: Union[str, Sequence[str], None] = (
    "f7a9c2e1b304",
    "b4c6d8e2f901",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""merge clients screening and core migration heads

Revision ID: f0a1b2c3d4e5
Revises: 9e7f6a1b2c34, e4f5a6b7c8d9
Create Date: 2026-09-07
"""

from typing import Sequence, Union


revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = (
    "9e7f6a1b2c34",
    "e4f5a6b7c8d9",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

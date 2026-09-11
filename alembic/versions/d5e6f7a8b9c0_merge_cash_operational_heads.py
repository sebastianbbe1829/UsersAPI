"""merge cash operational migration heads

Revision ID: d5e6f7a8b9c0
Revises: c2d3e4f5a6b7, c4d5e6f7a8b9
Create Date: 2026-09-11
"""

from typing import Sequence, Union

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = (
    "c2d3e4f5a6b7",
    "c4d5e6f7a8b9",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

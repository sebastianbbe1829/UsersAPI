"""merge cash traceability migration heads

Revision ID: a7b8c9d0e1f2
Revises: d5e6f7a8b9c0, f4c8a1b2d3e4
Create Date: 2026-09-10
"""

from typing import Sequence, Union

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = (
    "d5e6f7a8b9c0",
    "f4c8a1b2d3e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

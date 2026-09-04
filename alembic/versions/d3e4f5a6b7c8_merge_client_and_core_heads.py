"""merge client and core migration heads

Revision ID: d3e4f5a6b7c8
Revises: 1a2b3c4d5e6f, c0d1e2f3a4b5
Create Date: 2026-09-04
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = (
    "1a2b3c4d5e6f",
    "c0d1e2f3a4b5",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

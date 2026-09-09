"""merge sales POS migration heads

Revision ID: e3f5a7c9d1b2
Revises: e1a2b3c4d5e6, e2f4a6b8c0d2
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e3f5a7c9d1b2"
down_revision: Union[str, Sequence[str], None] = (
    "e1a2b3c4d5e6",
    "e2f4a6b8c0d2",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

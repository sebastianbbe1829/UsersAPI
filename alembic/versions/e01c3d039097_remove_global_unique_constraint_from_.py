"""remove global unique constraint from user dni

Revision ID: e01c3d039097
Revises: 0cd4289ed621
Create Date: 2026-08-20 19:21:39.837668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e01c3d039097'
down_revision: Union[str, Sequence[str], None] = '0cd4289ed621'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

"""remove global unique constraint from user dni

Revision ID: f0ffaafa9330
Revises: e01c3d039097
Create Date: 2026-08-20 19:22:49.761817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0ffaafa9330'
down_revision: Union[str, Sequence[str], None] = 'e01c3d039097'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

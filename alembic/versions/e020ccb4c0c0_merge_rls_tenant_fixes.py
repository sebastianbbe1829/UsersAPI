"""merge rls tenant fixes

Revision ID: e020ccb4c0c0
Revises: 5a9dd5c6b016, a44c1eed7f2e
Create Date: 2026-08-22 13:58:03.381735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e020ccb4c0c0'
down_revision: Union[str, Sequence[str], None] = ('5a9dd5c6b016', 'a44c1eed7f2e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

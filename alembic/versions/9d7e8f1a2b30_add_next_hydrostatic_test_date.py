"""add next hydrostatic test date

Revision ID: 9d7e8f1a2b30
Revises: 8c4d6e2f1a90
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9d7e8f1a2b30"
down_revision: Union[str, Sequence[str], None] = "8c4d6e2f1a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
INSPECTIONS = "extinguisher_inspections"
EXTINGUISHERS = "extinguishers"


def upgrade() -> None:
    op.add_column(
        INSPECTIONS,
        sa.Column("next_hydrostatic_test_date", sa.Date(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(INSPECTIONS, "next_hydrostatic_test_date", schema=SCHEMA)

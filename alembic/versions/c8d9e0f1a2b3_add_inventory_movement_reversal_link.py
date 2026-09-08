"""add reversal link to inventory movements

Revision ID: c8d9e0f1a2b3
Revises: b7c4d5e6f7a8
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column(
        "inventory_movements",
        sa.Column("reversal_of_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_inventory_movements_reversal_of",
        "inventory_movements",
        "inventory_movements",
        ["reversal_of_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_inventory_movements_reversal_of_id",
        "inventory_movements",
        ["reversal_of_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_api_inventory_movements_reversal_of_id",
        table_name="inventory_movements",
        schema=SCHEMA,
    )
    op.drop_constraint(
        "fk_inventory_movements_reversal_of",
        "inventory_movements",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.drop_column("inventory_movements", "reversal_of_id", schema=SCHEMA)

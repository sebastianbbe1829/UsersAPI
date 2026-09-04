"""add DANE attributes to cities table

Revision ID: 7b1c9d2e4f60
Revises: d3e4f5a6b7c8
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b1c9d2e4f60"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column(
        "cities",
        sa.Column("type", sa.String(length=50), nullable=False, server_default=sa.text("'Municipio'")),
        schema=SCHEMA,
    )
    op.add_column(
        "cities",
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "cities",
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("cities", "longitude", schema=SCHEMA)
    op.drop_column("cities", "latitude", schema=SCHEMA)
    op.drop_column("cities", "type", schema=SCHEMA)

"""add product image metadata

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
TABLE = "products"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("image_url", sa.String(length=1000), nullable=True), schema=SCHEMA)
    op.add_column(TABLE, sa.Column("image_source", sa.String(length=30), nullable=True), schema=SCHEMA)
    op.add_column(TABLE, sa.Column("image_source_url", sa.String(length=1000), nullable=True), schema=SCHEMA)
    op.add_column(TABLE, sa.Column("image_credit", sa.String(length=200), nullable=True), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column(TABLE, "image_credit", schema=SCHEMA)
    op.drop_column(TABLE, "image_source_url", schema=SCHEMA)
    op.drop_column(TABLE, "image_source", schema=SCHEMA)
    op.drop_column(TABLE, "image_url", schema=SCHEMA)

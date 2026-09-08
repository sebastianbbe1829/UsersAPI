"""add product brand and presentation fields

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("brand", sa.String(length=100), nullable=True),
        schema="users_api",
    )
    op.add_column(
        "products",
        sa.Column("presentation", sa.String(length=100), nullable=True),
        schema="users_api",
    )


def downgrade() -> None:
    op.drop_column("products", "presentation", schema="users_api")
    op.drop_column("products", "brand", schema="users_api")

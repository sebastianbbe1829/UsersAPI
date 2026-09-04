"""add official country catalog fields

Revision ID: 8c2d3e4f5a61
Revises: 7b1c9d2e4f60
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c2d3e4f5a61"
down_revision: Union[str, Sequence[str], None] = "7b1c9d2e4f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column("countries", sa.Column("short_name_lower", sa.String(length=100), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("full_name", sa.String(length=200), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("alpha3_code", sa.String(length=3), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("numeric_code", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("remarks", sa.String(length=500), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("independent", sa.Boolean(), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("territory_name", sa.String(length=250), nullable=True), schema=SCHEMA)
    op.add_column("countries", sa.Column("status", sa.String(length=50), nullable=True), schema=SCHEMA)

    op.create_index("ix_users_api_countries_alpha3_code", "countries", ["alpha3_code"], unique=True, schema=SCHEMA)
    op.create_index("ix_users_api_countries_numeric_code", "countries", ["numeric_code"], unique=True, schema=SCHEMA)

    op.execute(
        """
        UPDATE users_api.countries
        SET
            code = 'CO',
            name = 'COLOMBIA',
            short_name_lower = 'Colombia',
            full_name = 'the Republic of Colombia',
            alpha3_code = 'COL',
            numeric_code = 170,
            remarks = NULL,
            independent = TRUE,
            territory_name = 'Malpelo Island, San Andrés y Providencia Islands',
            status = 'Officially assigned',
            active = TRUE
        WHERE code = 'CO'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_api_countries_numeric_code", table_name="countries", schema=SCHEMA)
    op.drop_index("ix_users_api_countries_alpha3_code", table_name="countries", schema=SCHEMA)
    op.drop_column("countries", "status", schema=SCHEMA)
    op.drop_column("countries", "territory_name", schema=SCHEMA)
    op.drop_column("countries", "independent", schema=SCHEMA)
    op.drop_column("countries", "remarks", schema=SCHEMA)
    op.drop_column("countries", "numeric_code", schema=SCHEMA)
    op.drop_column("countries", "alpha3_code", schema=SCHEMA)
    op.drop_column("countries", "full_name", schema=SCHEMA)
    op.drop_column("countries", "short_name_lower", schema=SCHEMA)

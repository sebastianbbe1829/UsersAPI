"""add generic OTP codes

Revision ID: d9e4f7a1b203
Revises: c3f8a1d6b204
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d9e4f7a1b203"
down_revision: Union[str, Sequence[str], None] = "c3f8a1d6b204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("destination", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="users_api",
    )

    op.create_index(
        "ix_otp_codes_purpose",
        "otp_codes",
        ["purpose"],
        unique=False,
        schema="users_api",
    )
    op.create_index(
        "ix_otp_codes_purpose_destination",
        "otp_codes",
        ["purpose", "destination"],
        unique=False,
        schema="users_api",
    )
    op.create_index(
        "ix_otp_codes_expires_at",
        "otp_codes",
        ["expires_at"],
        unique=False,
        schema="users_api",
    )


def downgrade() -> None:
    op.drop_index("ix_otp_codes_expires_at", table_name="otp_codes", schema="users_api")
    op.drop_index("ix_otp_codes_purpose_destination", table_name="otp_codes", schema="users_api")
    op.drop_index("ix_otp_codes_purpose", table_name="otp_codes", schema="users_api")
    op.drop_table("otp_codes", schema="users_api")

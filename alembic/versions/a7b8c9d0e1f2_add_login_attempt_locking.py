"""add tenant login attempt locking and audit identifiers

Revision ID: a7b8c9d0e1f2
Revises: f1b2c3d4e567
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1b2c3d4e567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column(
        "tenant_configs",
        sa.Column(
            "max_login_attempts",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("0"),
        ),
        schema=SCHEMA,
    )

    op.add_column(
        "user_tenants",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        schema=SCHEMA,
    )
    op.add_column(
        "user_tenants",
        sa.Column("last_failed_login_at", sa.DateTime(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "user_tenants",
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "user_tenants",
        sa.Column("locked_ip", sa.String(length=45), nullable=True),
        schema=SCHEMA,
    )

    op.add_column(
        "auth_audit",
        sa.Column("actor_dni", sa.String(length=100), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "auth_audit",
        sa.Column("actor_login", sa.String(length=255), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("auth_audit", "actor_login", schema=SCHEMA)
    op.drop_column("auth_audit", "actor_dni", schema=SCHEMA)
    op.drop_column("user_tenants", "locked_ip", schema=SCHEMA)
    op.drop_column("user_tenants", "locked_at", schema=SCHEMA)
    op.drop_column("user_tenants", "last_failed_login_at", schema=SCHEMA)
    op.drop_column("user_tenants", "failed_login_attempts", schema=SCHEMA)
    op.drop_column("tenant_configs", "max_login_attempts", schema=SCHEMA)

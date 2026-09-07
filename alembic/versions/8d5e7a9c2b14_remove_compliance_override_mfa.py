"""remove MFA requirement from compliance override

Revision ID: 8d5e7a9c2b14
Revises: 7b4c9d2e1f30
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8d5e7a9c2b14"
down_revision: Union[str, Sequence[str], None] = "7b4c9d2e1f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column(
        "client_compliance_overrides",
        "mfa_verified_at",
        schema="users_api",
    )
    op.execute(
        sa.text(
            """
            UPDATE users_api.permissions
            SET description = :description
            WHERE code = 'CLIENT_COMPLIANCE_OVERRIDE'
            """
        ).bindparams(
            description="Permite levantar una restricción de compliance de un cliente",
        )
    )


def downgrade() -> None:
    op.add_column(
        "client_compliance_overrides",
        sa.Column("mfa_verified_at", sa.DateTime(), nullable=True),
        schema="users_api",
    )

"""add MFA verification state for global users

Revision ID: 7b2e4f6a91c3
Revises: 6c5f8a9b21d4
Create Date: 2026-08-27

"""

from typing import Sequence, Union

from alembic import op


revision: str = "7b2e4f6a91c3"
down_revision: Union[str, Sequence[str], None] = "6c5f8a9b21d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users_api.global_users
        ADD COLUMN mfa_verified_at timestamp;
        """
    )

    # Los SUPER existentes fueron creados mediante el flujo anterior,
    # en el cual MFA ya quedaba habilitado. Se consideran verificados
    # para no invalidar sesiones/configuraciones existentes.
    op.execute(
        """
        UPDATE users_api.global_users
        SET mfa_verified_at = COALESCE(
            updated_at,
            created_at,
            CURRENT_TIMESTAMP
        )
        WHERE mfa_enabled = true
          AND mfa_secret_encrypted IS NOT NULL
          AND mfa_verified_at IS NULL;
        """
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE
        ON TABLE users_api.global_users
        TO users_api_app;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE users_api.global_users
        DROP COLUMN IF EXISTS mfa_verified_at;
        """
    )

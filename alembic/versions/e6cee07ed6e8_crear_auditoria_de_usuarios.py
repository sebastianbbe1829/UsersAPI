"""crear auditoria de usuarios

Revision ID: e6cee07ed6e8
Revises: 9de3efc251f7
Create Date: 2026-08-18 20:01:03.728561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6cee07ed6e8'
down_revision: Union[str, Sequence[str], None] = '9de3efc251f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crear función y trigger de auditoría."""

    # --------------------------------------------------------
    # FUNCIÓN DE AUDITORÍA
    # --------------------------------------------------------

    op.execute(
        """
        CREATE OR REPLACE FUNCTION users_api.fn_app_users_audit()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_by_bd := CURRENT_USER;
            RETURN NEW;
        END;
        $$;
        """
    )

    # --------------------------------------------------------
    # TRIGGER
    # --------------------------------------------------------

    op.execute(
        """
        CREATE TRIGGER trg_app_users_audit
        BEFORE UPDATE ON users_api.app_users
        FOR EACH ROW
        EXECUTE FUNCTION users_api.fn_app_users_audit();
        """
    )


def downgrade() -> None:
    """Eliminar trigger y función."""

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_app_users_audit
        ON users_api.app_users;
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS users_api.fn_app_users_audit();
        """
    )
"""mover credenciales fuera de app_users

Revision ID: b7c2d9e4f1a6
Revises: 672515f72708
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7c2d9e4f1a6"
down_revision: Union[str, Sequence[str], None] = "672515f72708"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_COLUMNS = (
    "activation_token",
    "email",
    "status",
    "phone",
    "password",
)


def upgrade() -> None:
    op.drop_index(
        "ix_users_api_app_users_activation_token",
        table_name="app_users",
        schema="users_api",
    )
    op.drop_index(
        "ix_users_api_app_users_email",
        table_name="app_users",
        schema="users_api",
    )
    for column in LEGACY_COLUMNS:
        op.drop_column("app_users", column, schema="users_api")


def downgrade() -> None:
    raise RuntimeError(
        "No se puede restaurar credenciales de app_users sin una fuente tenant explícita"
    )

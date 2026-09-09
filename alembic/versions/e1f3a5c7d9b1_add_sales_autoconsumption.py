"""add sales autoconsumption

Revision ID: e1f3a5c7d9b1
Revises: d9e0f1a2b3c4
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f3a5c7d9b1"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column(
            "is_autoconsumption",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema=SCHEMA,
    )

    op.execute(
        """
        INSERT INTO users_api.permissions (code, name, description, status, created_by)
        VALUES (
            'SALES_AUTOCONSUME',
            'Autorizar autoconsumo',
            'Permite registrar ventas a precio de compra sin ganancia',
            1,
            'SYSTEM'
        )
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            description = EXCLUDED.description,
            status = 1
        """
    )
    op.execute(
        """
        INSERT INTO users_api.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM users_api.roles r
        CROSS JOIN users_api.permissions p
        WHERE r.code = 'ADMIN'
          AND p.code = 'SALES_AUTOCONSUME'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM users_api.role_permissions
        WHERE permission_id IN (
            SELECT id FROM users_api.permissions
            WHERE code = 'SALES_AUTOCONSUME'
        )
        """
    )
    op.execute(
        """
        DELETE FROM users_api.permissions
        WHERE code = 'SALES_AUTOCONSUME'
        """
    )
    op.drop_column("sales", "is_autoconsumption", schema=SCHEMA)

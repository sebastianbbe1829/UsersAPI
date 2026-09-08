"""add sales invoice permission

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""

from alembic import op


revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO users_api.permissions (code, name, description, status, created_by)
        VALUES (
            'SALES_EMAIL',
            'Enviar factura por correo',
            'Permite enviar la factura de una venta a los clientes registrados',
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
          AND p.code = 'SALES_EMAIL'
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM users_api.role_permissions
        WHERE permission_id IN (
            SELECT id FROM users_api.permissions WHERE code = 'SALES_EMAIL'
        )
        """
    )
    op.execute(
        """
        DELETE FROM users_api.permissions WHERE code = 'SALES_EMAIL'
        """
    )

"""crear estructura multi tenant

Revision ID: 0f44051a723f
Revises: e6cee07ed6e8
Create Date: 2026-08-18 22:04:45.335170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f44051a723f'
down_revision: Union[str, Sequence[str], None] = 'e6cee07ed6e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade() -> None:
    """
    Crea la estructura inicial multi-tenant.

    - tenants
    - user_tenants

    Los usuarios existentes se asocian automáticamente
    al Tenant Demo.
    """

    # ========================================================
    # 1. CREAR TABLA TENANTS
    # ========================================================

    op.create_table(
        "tenants",

        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(
                always=False,
                start=1,
                increment=1,
            ),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),

        sa.Column(
            "slug",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "created_by",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "created_by_bd",
            sa.String(length=100),
            nullable=True,
            server_default=sa.text("USER"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "updated_by",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "updated_by_bd",
            sa.String(length=100),
            nullable=True,
            server_default=sa.text("USER"),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "slug",
            name="uq_tenants_slug",
        ),

        schema="users_api",
    )

    # ========================================================
    # 2. ÍNDICES TENANTS
    # ========================================================

    op.create_index(
        "ix_users_api_tenants_name",
        "tenants",
        ["name"],
        unique=False,
        schema="users_api",
    )

    op.create_index(
        "ix_users_api_tenants_slug",
        "tenants",
        ["slug"],
        unique=True,
        schema="users_api",
    )

    # ========================================================
    # 3. CREAR TABLA USER_TENANTS
    # ========================================================

    op.create_table(
        "user_tenants",

        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(
                always=False,
                start=1,
                increment=1,
            ),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "tenant_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "created_by",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "created_by_bd",
            sa.String(length=100),
            nullable=True,
            server_default=sa.text("USER"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "updated_by",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "updated_by_bd",
            sa.String(length=100),
            nullable=True,
            server_default=sa.text("USER"),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users_api.app_users.id"],
            name="fk_user_tenants_user",
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["users_api.tenants.id"],
            name="fk_user_tenants_tenant",
            ondelete="CASCADE",
        ),

        sa.UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_user_tenants_user_tenant",
        ),

        schema="users_api",
    )

    # ========================================================
    # 4. ÍNDICES USER_TENANTS
    # ========================================================

    op.create_index(
        "ix_users_api_user_tenants_user_id",
        "user_tenants",
        ["user_id"],
        unique=False,
        schema="users_api",
    )

    op.create_index(
        "ix_users_api_user_tenants_tenant_id",
        "user_tenants",
        ["tenant_id"],
        unique=False,
        schema="users_api",
    )

    # ========================================================
    # 5. CREAR TENANT DEMO
    # ========================================================

    op.execute(
        """
        INSERT INTO users_api.tenants
        (
            name,
            slug,
            status,
            created_at,
            created_by
        )
        VALUES
        (
            'Tenant Demo',
            'tenant-demo',
            1,
            CURRENT_TIMESTAMP,
            'system'
        )
        """
    )

    # ========================================================
    # 6. ASOCIAR TODOS LOS USUARIOS EXISTENTES
    #    AL TENANT DEMO
    # ========================================================

    op.execute(
        """
        INSERT INTO users_api.user_tenants
        (
            user_id,
            tenant_id,
            status,
            created_at,
            created_by
        )
        SELECT
            u.id,
            t.id,
            1,
            CURRENT_TIMESTAMP,
            'system'
        FROM users_api.app_users u
        CROSS JOIN users_api.tenants t
        WHERE t.slug = 'tenant-demo'
        """
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade() -> None:
    """
    Elimina la estructura multi-tenant.
    """

    op.drop_index(
        "ix_users_api_user_tenants_tenant_id",
        table_name="user_tenants",
        schema="users_api",
    )

    op.drop_index(
        "ix_users_api_user_tenants_user_id",
        table_name="user_tenants",
        schema="users_api",
    )

    op.drop_table(
        "user_tenants",
        schema="users_api",
    )

    op.drop_index(
        "ix_users_api_tenants_slug",
        table_name="tenants",
        schema="users_api",
    )

    op.drop_index(
        "ix_users_api_tenants_name",
        table_name="tenants",
        schema="users_api",
    )

    op.drop_table(
        "tenants",
        schema="users_api",
    )
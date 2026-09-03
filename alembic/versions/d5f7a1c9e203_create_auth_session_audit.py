"""create authentication session audit

Revision ID: d5f7a1c9e203
Revises: c1d2e3f4a5b6, c3f8a1d6b204
Create Date: 2026-09-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f7a1c9e203"
down_revision: Union[str, Sequence[str], None] = (
    "c1d2e3f4a5b6",
    "c3f8a1d6b204",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def _rls_policy(table: str) -> None:
    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.{table}
        ENABLE ROW LEVEL SECURITY
        """
    )
    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.{table}
        FORCE ROW LEVEL SECURITY
        """
    )
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation
        ON {SCHEMA}.{table}
        USING (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        """
    )


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_tenant_id", sa.Integer(), nullable=True),
        sa.Column("global_user_id", sa.Integer(), nullable=True),
        sa.Column("session_kind", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "login_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("logout_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_tenant_id"],
            [f"{SCHEMA}.user_tenants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["global_user_id"],
            [f"{SCHEMA}.global_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_sessions_tenant_id",
        "auth_sessions",
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_sessions_user_tenant_id",
        "auth_sessions",
        ["user_tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_sessions_global_user_id",
        "auth_sessions",
        ["global_user_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_sessions_token_hash",
        "auth_sessions",
        ["token_hash"],
        unique=False,
        schema=SCHEMA,
    )
    _rls_policy("auth_sessions")

    op.create_table(
        "auth_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_tenant_id", sa.Integer(), nullable=True),
        sa.Column("global_user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("session_kind", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("actor_identifier", sa.String(length=255), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=1000), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_tenant_id"],
            [f"{SCHEMA}.user_tenants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["global_user_id"],
            [f"{SCHEMA}.global_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_audit_tenant_id",
        "auth_audit",
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_audit_occurred_at",
        "auth_audit",
        ["occurred_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_auth_audit_session_id",
        "auth_audit",
        ["session_id"],
        unique=False,
        schema=SCHEMA,
    )
    _rls_policy("auth_audit")


def downgrade() -> None:
    for table in ("auth_audit", "auth_sessions"):
        op.execute(
            f"""
            DROP POLICY IF EXISTS {table}_tenant_isolation
            ON {SCHEMA}.{table}
            """
        )
        op.execute(
            f"""
            ALTER TABLE {SCHEMA}.{table}
            NO FORCE ROW LEVEL SECURITY
            """
        )
        op.execute(
            f"""
            ALTER TABLE {SCHEMA}.{table}
            DISABLE ROW LEVEL SECURITY
            """
        )

    op.drop_index(
        "ix_users_api_auth_audit_session_id",
        table_name="auth_audit",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_auth_audit_occurred_at",
        table_name="auth_audit",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_auth_audit_tenant_id",
        table_name="auth_audit",
        schema=SCHEMA,
    )
    op.drop_table("auth_audit", schema=SCHEMA)

    op.drop_index(
        "ix_users_api_auth_sessions_token_hash",
        table_name="auth_sessions",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_auth_sessions_global_user_id",
        table_name="auth_sessions",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_auth_sessions_user_tenant_id",
        table_name="auth_sessions",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_auth_sessions_tenant_id",
        table_name="auth_sessions",
        schema=SCHEMA,
    )
    op.drop_table("auth_sessions", schema=SCHEMA)

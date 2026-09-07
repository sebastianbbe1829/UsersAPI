"""add client compliance override

Revision ID: 7b4c9d2e1f30
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "7b4c9d2e1f30"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
SCHEMA = "users_api"
PERMISSION_CODE = "CLIENT_COMPLIANCE_OVERRIDE"


def upgrade() -> None:
    op.create_check_constraint(
        "ck_clients_status",
        "clients",
        "status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')",
        schema=SCHEMA,
    )

    op.create_table(
        "client_compliance_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("screening_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("requested_by_email", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("mfa_verified_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], [f"{SCHEMA}.clients.id"]),
        sa.ForeignKeyConstraint(["screening_id"], [f"{SCHEMA}.client_screenings.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_client_compliance_overrides_tenant_id",
        "client_compliance_overrides",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_client_compliance_overrides_client_id",
        "client_compliance_overrides",
        ["client_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_client_compliance_overrides_screening_id",
        "client_compliance_overrides",
        ["screening_id"],
        schema=SCHEMA,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO users_api.permissions
                (code, name, description, status, created_by)
            VALUES
                (:code, :name, :description, 1, 'clients-compliance-migration')
            ON CONFLICT (code) DO NOTHING
            """
        ).bindparams(
            code=PERMISSION_CODE,
            name="Levantar restricción de cliente",
            description="Permite levantar una restricción de compliance mediante MFA",
        )
    )

    op.execute(f"ALTER TABLE {SCHEMA}.client_compliance_overrides ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {SCHEMA}.client_compliance_overrides FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""CREATE POLICY client_compliance_overrides_isolation ON {SCHEMA}.client_compliance_overrides
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)"""
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS client_compliance_overrides_isolation ON users_api.client_compliance_overrides"
    )
    op.execute(
        "ALTER TABLE users_api.client_compliance_overrides NO FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE users_api.client_compliance_overrides DISABLE ROW LEVEL SECURITY"
    )
    for index_name in (
        "ix_users_api_client_compliance_overrides_screening_id",
        "ix_users_api_client_compliance_overrides_client_id",
        "ix_users_api_client_compliance_overrides_tenant_id",
    ):
        op.drop_index(index_name, table_name="client_compliance_overrides", schema=SCHEMA)
    op.drop_table("client_compliance_overrides", schema=SCHEMA)
    op.drop_constraint("ck_clients_status", "clients", schema=SCHEMA, type_="check")

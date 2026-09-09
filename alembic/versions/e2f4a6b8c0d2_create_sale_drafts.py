"""create sale drafts

Revision ID: e2f4a6b8c0d2
Revises: e1f3a5c7d9b1
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e2f4a6b8c0d2"
down_revision: Union[str, Sequence[str], None] = "e1f3a5c7d9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.create_table(
        "sale_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("draft_number", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "draft_number", name="uq_sale_drafts_tenant_number"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_sale_drafts_tenant_id", "sale_drafts", ["tenant_id"], schema=SCHEMA)

    op.execute(
        f"""ALTER TABLE {SCHEMA}.sale_drafts ENABLE ROW LEVEL SECURITY"""
    )
    op.execute(
        f"""ALTER TABLE {SCHEMA}.sale_drafts FORCE ROW LEVEL SECURITY"""
    )
    op.execute(
        f"""CREATE POLICY sale_drafts_tenant_isolation ON {SCHEMA}.sale_drafts
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)"""
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS sale_drafts_tenant_isolation ON {SCHEMA}.sale_drafts")
    op.execute(f"ALTER TABLE {SCHEMA}.sale_drafts NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {SCHEMA}.sale_drafts DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_users_api_sale_drafts_tenant_id", table_name="sale_drafts", schema=SCHEMA)
    op.drop_table("sale_drafts", schema=SCHEMA)

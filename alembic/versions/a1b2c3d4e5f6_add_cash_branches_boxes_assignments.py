"""add cash branches, boxes and user assignments

Revision ID: a1b2c3d4e5f6
Revises: f7c8d9e0a1b2
Create Date: 2026-09-09
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f7c8d9e0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_user_tenants_tenant_id", "user_tenants", ["tenant_id", "id"], schema="users_api")
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False), sa.Column("code", sa.String(30), nullable=False), sa.Column("name", sa.String(150), nullable=False),
        sa.Column("address", sa.String(250)), sa.Column("phone", sa.String(30)), sa.Column("status", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("created_by", sa.String(100), nullable=False), sa.Column("updated_at", sa.DateTime()), sa.Column("updated_by", sa.String(100)),
        sa.ForeignKeyConstraint(["tenant_id"], ["users_api.tenants.id"], ondelete="CASCADE"), sa.UniqueConstraint("tenant_id", "id", name="uq_branches_tenant_id"), schema="users_api")
    op.create_index("uq_branches_tenant_code", "branches", ["tenant_id", "code"], unique=True, schema="users_api")
    op.create_index("ix_branches_tenant_id", "branches", ["tenant_id"], schema="users_api")

    op.create_table(
        "cash_boxes",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True), sa.Column("tenant_id", sa.Integer(), nullable=False), sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(30), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("status", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("created_by", sa.String(100), nullable=False), sa.Column("updated_at", sa.DateTime()), sa.Column("updated_by", sa.String(100)),
        sa.ForeignKeyConstraint(["tenant_id", "branch_id"], ["users_api.branches.tenant_id", "users_api.branches.id"], ondelete="CASCADE"), sa.UniqueConstraint("tenant_id", "id", name="uq_cash_boxes_tenant_id"), schema="users_api")
    op.create_index("uq_cash_boxes_branch_code", "cash_boxes", ["branch_id", "code"], unique=True, schema="users_api")
    op.create_index("ix_cash_boxes_tenant_id", "cash_boxes", ["tenant_id"], schema="users_api")

    op.create_table(
        "user_cash_assignments",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True), sa.Column("tenant_id", sa.Integer(), nullable=False), sa.Column("user_tenant_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False), sa.Column("cash_box_id", sa.Integer(), nullable=False), sa.Column("status", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), sa.Column("assigned_by", sa.String(100), nullable=False), sa.Column("unassigned_at", sa.DateTime()), sa.Column("unassigned_by", sa.String(100)),
        sa.ForeignKeyConstraint(["tenant_id", "user_tenant_id"], ["users_api.user_tenants.tenant_id", "users_api.user_tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "branch_id"], ["users_api.branches.tenant_id", "users_api.branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id", "cash_box_id"], ["users_api.cash_boxes.tenant_id", "users_api.cash_boxes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_user_cash_assignments_tenant_id"), schema="users_api")
    op.create_index("uq_user_cash_assignments_active_user", "user_cash_assignments", ["tenant_id", "user_tenant_id"], unique=True, postgresql_where=sa.text("status = 1"), schema="users_api")
    op.create_index("ix_user_cash_assignments_tenant_id", "user_cash_assignments", ["tenant_id"], schema="users_api")

    op.drop_index("uq_cash_registers_open_tenant", table_name="cash_registers", schema="users_api")
    op.add_column("cash_registers", sa.Column("branch_id", sa.Integer(), nullable=True), schema="users_api")
    op.add_column("cash_registers", sa.Column("cash_box_id", sa.Integer(), nullable=True), schema="users_api")
    op.add_column("cash_registers", sa.Column("business_date", sa.Date(), nullable=True), schema="users_api")
    op.create_foreign_key("fk_cash_registers_branch", "cash_registers", "branches", ["tenant_id", "branch_id"], ["tenant_id", "id"], source_schema="users_api", referent_schema="users_api")
    op.create_foreign_key("fk_cash_registers_cash_box", "cash_registers", "cash_boxes", ["tenant_id", "cash_box_id"], ["tenant_id", "id"], source_schema="users_api", referent_schema="users_api")
    op.create_index("uq_cash_registers_open_box", "cash_registers", ["cash_box_id"], unique=True, postgresql_where=sa.text("status = 'OPEN'"), schema="users_api")
    op.create_index("uq_cash_registers_box_business_date", "cash_registers", ["cash_box_id", "business_date"], unique=True, schema="users_api")
    op.create_index("ix_cash_registers_branch_id", "cash_registers", ["branch_id"], schema="users_api")
    op.create_index("ix_cash_registers_cash_box_id", "cash_registers", ["cash_box_id"], schema="users_api")

    for table, policy in (("branches", "branches_isolation"), ("cash_boxes", "cash_boxes_isolation"), ("user_cash_assignments", "user_cash_assignments_isolation")):
        op.execute(f"ALTER TABLE users_api.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {policy} ON users_api.{table} USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer) WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer)")


def downgrade() -> None:
    for table, policy in (("user_cash_assignments", "user_cash_assignments_isolation"), ("cash_boxes", "cash_boxes_isolation"), ("branches", "branches_isolation")):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON users_api.{table}")
    op.drop_index("ix_cash_registers_cash_box_id", table_name="cash_registers", schema="users_api"); op.drop_index("ix_cash_registers_branch_id", table_name="cash_registers", schema="users_api"); op.drop_index("uq_cash_registers_box_business_date", table_name="cash_registers", schema="users_api"); op.drop_index("uq_cash_registers_open_box", table_name="cash_registers", schema="users_api")
    op.drop_constraint("fk_cash_registers_cash_box", "cash_registers", schema="users_api", type_="foreignkey"); op.drop_constraint("fk_cash_registers_branch", "cash_registers", schema="users_api", type_="foreignkey")
    op.drop_column("cash_registers", "business_date", schema="users_api"); op.drop_column("cash_registers", "cash_box_id", schema="users_api"); op.drop_column("cash_registers", "branch_id", schema="users_api")
    op.create_index("uq_cash_registers_open_tenant", "cash_registers", ["tenant_id"], unique=True, postgresql_where=sa.text("status = 'OPEN'"), schema="users_api")
    op.drop_index("ix_user_cash_assignments_tenant_id", table_name="user_cash_assignments", schema="users_api"); op.drop_index("uq_user_cash_assignments_active_user", table_name="user_cash_assignments", schema="users_api"); op.drop_table("user_cash_assignments", schema="users_api")
    op.drop_index("ix_cash_boxes_tenant_id", table_name="cash_boxes", schema="users_api"); op.drop_index("uq_cash_boxes_branch_code", table_name="cash_boxes", schema="users_api"); op.drop_table("cash_boxes", schema="users_api")
    op.drop_index("ix_branches_tenant_id", table_name="branches", schema="users_api"); op.drop_index("uq_branches_tenant_code", table_name="branches", schema="users_api"); op.drop_table("branches", schema="users_api")
    op.drop_constraint("uq_user_tenants_tenant_id", "user_tenants", schema="users_api", type_="unique")

"""create screening sync executions

Revision ID: 8c5d7e9f1a2b
Revises: 8d5e7a9c2b14
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "8c5d7e9f1a2b"
down_revision: Union[str, Sequence[str], None] = "8d5e7a9c2b14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
SCHEMA = "users_api"


def upgrade() -> None:
    op.create_table(
        "screening_sync_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("triggered_by_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("total_sources", sa.Integer(), nullable=True),
        sa.Column("successful_sources", sa.Integer(), nullable=True),
        sa.Column("failed_sources", sa.Integer(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_screening_sync_executions_created_at",
        "screening_sync_executions",
        ["created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "uq_users_api_screening_sync_execution_active",
        "screening_sync_executions",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'RUNNING')"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_users_api_screening_sync_execution_active",
        table_name="screening_sync_executions",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_screening_sync_executions_created_at",
        table_name="screening_sync_executions",
        schema=SCHEMA,
    )
    op.drop_table("screening_sync_executions", schema=SCHEMA)

"""create extinguisher recharge notification log

Revision ID: b4c6d8e2f901
Revises: a1b2c3d4e5f6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b4c6d8e2f901"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
TABLE = "extinguisher_recharge_notification_log"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("notification_date", sa.Date(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            [f"{SCHEMA}.tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("notification_date", "tenant_id", "recipient"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table(TABLE, schema=SCHEMA)

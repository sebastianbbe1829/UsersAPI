"""remove unused extinguisher recharges table

Revision ID: a1b2c3d4e5f6
Revises: 9d7e8f1a2b30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9d7e8f1a2b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
TABLE = "extinguisher_recharges"


def upgrade() -> None:
    # The recharge feature was never used by the application.
    # IF EXISTS keeps the migration safe for databases where the table
    # was not created in the first place.
    op.execute(
        sa.text(
            f'DROP TABLE IF EXISTS "{SCHEMA}"."{TABLE}" CASCADE'
        )
    )


def downgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("extinguisher_id", sa.Integer(), nullable=False),
        sa.Column("recharge_date", sa.Date(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extinguisher_id"], [f"{SCHEMA}.extinguishers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.user_tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    op.create_index(
        f"ix_{TABLE}_tenant_id",
        TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        f"ix_{TABLE}_extinguisher_id",
        TABLE,
        ["extinguisher_id"],
        unique=False,
        schema=SCHEMA,
    )

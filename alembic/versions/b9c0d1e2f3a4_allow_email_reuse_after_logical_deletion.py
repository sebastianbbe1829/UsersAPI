"""allow tenant email reuse after logical deletion

Revision ID: b9c0d1e2f3a4
Revises: a7b8c9d0e1f2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
OLD_CONSTRAINT = "uq_user_tenants_tenant_email"
NEW_INDEX = "uq_user_tenants_tenant_email_active"


def upgrade() -> None:
    op.drop_constraint(
        OLD_CONSTRAINT,
        "user_tenants",
        schema=SCHEMA,
        type_="unique",
    )

    op.create_index(
        NEW_INDEX,
        "user_tenants",
        ["tenant_id", "email"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("status <> 3"),
    )


def downgrade() -> None:
    op.drop_index(
        NEW_INDEX,
        table_name="user_tenants",
        schema=SCHEMA,
    )

    op.create_unique_constraint(
        OLD_CONSTRAINT,
        "user_tenants",
        ["tenant_id", "email"],
        schema=SCHEMA,
    )

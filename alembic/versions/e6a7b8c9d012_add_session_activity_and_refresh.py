"""add session activity and refresh support"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e6a7b8c9d012"
down_revision: Union[str, Sequence[str], None] = "d5f7a1c9e203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
SCHEMA = "users_api"


def upgrade() -> None:
    op.add_column("auth_sessions", sa.Column("last_activity_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")), schema=SCHEMA)
    op.create_index("ix_users_api_auth_sessions_last_activity_at", "auth_sessions", ["last_activity_at"], unique=False, schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_users_api_auth_sessions_last_activity_at", table_name="auth_sessions", schema=SCHEMA)
    op.drop_column("auth_sessions", "last_activity_at", schema=SCHEMA)

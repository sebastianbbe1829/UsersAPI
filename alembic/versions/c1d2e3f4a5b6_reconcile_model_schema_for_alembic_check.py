"""reconcile model schema for alembic check

Revision ID: c1d2e3f4a5b6
Revises: b9e4f6a1c203
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b9e4f6a1c203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    # SUPER profile fields were added to the SQLAlchemy model after the
    # original global_users table migration. Keep them nullable for existing
    # rows and make fresh-database upgrades deterministic.
    op.execute(
        """
        ALTER TABLE users_api.global_users
        ADD COLUMN IF NOT EXISTS dni varchar(20),
        ADD COLUMN IF NOT EXISTS name varchar(100),
        ADD COLUMN IF NOT EXISTS phone varchar(30),
        ADD COLUMN IF NOT EXISTS mfa_verified_at timestamp
        """
    )

    # app_users: current model requires a name and keeps a non-unique DNI index.
    op.alter_column(
        "app_users",
        "name",
        nullable=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_app_users_dni",
        "app_users",
        ["dni"],
        unique=False,
        schema=SCHEMA,
        if_not_exists=True,
    )

    # Inspection catalog: SQLAlchemy models expose code as a unique indexed
    # column, which is represented in PostgreSQL as a unique index.
    op.drop_constraint(
        "uq_extinguisher_inspection_items_code",
        "extinguisher_inspection_items",
        type_="unique",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguisher_inspection_items_code",
        "extinguisher_inspection_items",
        ["code"],
        unique=True,
        schema=SCHEMA,
        if_not_exists=True,
    )

    # Inspection result index was renamed with the model field.
    op.drop_index(
        "ix_users_api_extinguisher_inspection_results_item_id",
        table_name="extinguisher_inspection_results",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguisher_inspection_results_inspection_item_id",
        "extinguisher_inspection_results",
        ["inspection_item_id"],
        unique=False,
        schema=SCHEMA,
        if_not_exists=True,
    )

    # Extinguisher type catalog: unique indexed code.
    op.drop_constraint(
        "uq_extinguisher_types_code",
        "extinguisher_types",
        type_="unique",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguisher_types_code",
        "extinguisher_types",
        ["code"],
        unique=True,
        schema=SCHEMA,
        if_not_exists=True,
    )

    # The current model intentionally no longer declares a tenant/code
    # composite uniqueness constraint.
    op.drop_constraint(
        "uq_extinguishers_tenant_code",
        "extinguishers",
        type_="unique",
        schema=SCHEMA,
    )

    # SUPER users: DNI and name are normal indexes; email/session semantics
    # are aligned with the current SQLAlchemy model.
    op.execute("DROP INDEX IF EXISTS users_api.uq_global_users_dni")
    op.create_index(
        "ix_users_api_global_users_dni",
        "global_users",
        ["dni"],
        unique=False,
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_users_api_global_users_name",
        "global_users",
        ["name"],
        unique=False,
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.drop_index(
        "ix_global_users_email",
        table_name="global_users",
        schema=SCHEMA,
    )
    op.drop_index(
        "uq_global_users_email_lower",
        table_name="global_users",
        schema=SCHEMA,
    )
    op.drop_constraint(
        "uq_global_users_session_id",
        "global_users",
        type_="unique",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_global_users_email",
        "global_users",
        ["email"],
        unique=False,
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_users_api_global_users_session_id",
        "global_users",
        ["session_id"],
        unique=True,
        schema=SCHEMA,
        if_not_exists=True,
    )

    # OTP purpose index name is aligned with the schema-qualified model
    # naming convention.
    op.drop_index(
        "ix_otp_codes_purpose",
        table_name="otp_codes",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_otp_codes_purpose",
        "otp_codes",
        ["purpose"],
        unique=False,
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_api_otp_codes_purpose",
        table_name="otp_codes",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_otp_codes_purpose",
        "otp_codes",
        ["purpose"],
        unique=False,
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_users_api_global_users_session_id",
        table_name="global_users",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_global_users_email",
        table_name="global_users",
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_global_users_session_id",
        "global_users",
        ["session_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_global_users_email",
        "global_users",
        ["email"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "uq_global_users_email_lower",
        "global_users",
        ["lower(email)"],
        unique=True,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_global_users_name",
        table_name="global_users",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_users_api_global_users_dni",
        table_name="global_users",
        schema=SCHEMA,
    )
    op.create_index(
        "uq_global_users_dni",
        "global_users",
        ["dni"],
        unique=True,
        schema=SCHEMA,
    )

    op.create_unique_constraint(
        "uq_extinguishers_tenant_code",
        "extinguishers",
        ["tenant_id", "code"],
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_users_api_extinguisher_types_code",
        table_name="extinguisher_types",
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_extinguisher_types_code",
        "extinguisher_types",
        ["code"],
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_users_api_extinguisher_inspection_results_inspection_item_id",
        table_name="extinguisher_inspection_results",
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_extinguisher_inspection_results_item_id",
        "extinguisher_inspection_results",
        ["inspection_item_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_users_api_extinguisher_inspection_items_code",
        table_name="extinguisher_inspection_items",
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_extinguisher_inspection_items_code",
        "extinguisher_inspection_items",
        ["code"],
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_users_api_app_users_dni",
        table_name="app_users",
        schema=SCHEMA,
    )
    op.alter_column(
        "app_users",
        "name",
        nullable=True,
        schema=SCHEMA,
    )

    op.execute(
        """
        ALTER TABLE users_api.global_users
        DROP COLUMN IF EXISTS mfa_verified_at,
        DROP COLUMN IF EXISTS phone,
        DROP COLUMN IF EXISTS name,
        DROP COLUMN IF EXISTS dni
        """
    )

"""create clients domain

Revision ID: 1a2b3c4d5e6f
Revises: f7a9c2e1b304
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "f7a9c2e1b304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.create_table(
        "identification_types",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("person_type", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_identification_types_code"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_users_api_identification_types_code",
        "identification_types",
        ["code"],
        unique=True,
        schema=SCHEMA,
    )

    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_countries_code"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_countries_code", "countries", ["code"], unique=True, schema=SCHEMA)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["country_id"], [f"{SCHEMA}.countries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country_id", "code", name="uq_departments_country_code"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_departments_country_id", "departments", ["country_id"], schema=SCHEMA)

    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["department_id"], [f"{SCHEMA}.departments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "code", name="uq_cities_department_code"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_cities_department_id", "cities", ["department_id"], schema=SCHEMA)

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("identification_type_id", sa.Integer(), nullable=False),
        sa.Column("identification_number", sa.String(length=50), nullable=False),
        sa.Column("person_type", sa.String(length=20), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("middle_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("second_last_name", sa.String(length=100), nullable=True),
        sa.Column("business_name", sa.String(length=250), nullable=True),
        sa.Column("full_name", sa.String(length=250), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.String(length=250), nullable=True),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("compliance_status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("is_listed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("list_type", sa.String(length=50), nullable=True),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("consent_at", sa.DateTime(), nullable=True),
        sa.Column("consent_source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["identification_type_id"], [f"{SCHEMA}.identification_types.id"]),
        sa.ForeignKeyConstraint(["country_id"], [f"{SCHEMA}.countries.id"]),
        sa.ForeignKeyConstraint(["department_id"], [f"{SCHEMA}.departments.id"]),
        sa.ForeignKeyConstraint(["city_id"], [f"{SCHEMA}.cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "identification_type_id",
            "identification_number",
            name="uq_clients_tenant_identification",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_clients_tenant_id", "clients", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_clients_identification_type_id", "clients", ["identification_type_id"], schema=SCHEMA)
    op.create_index("ix_users_api_clients_country_id", "clients", ["country_id"], schema=SCHEMA)
    op.create_index("ix_users_api_clients_department_id", "clients", ["department_id"], schema=SCHEMA)
    op.create_index("ix_users_api_clients_city_id", "clients", ["city_id"], schema=SCHEMA)

    op.create_table(
        "client_screenings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("response", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], [f"{SCHEMA}.tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], [f"{SCHEMA}.clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_client_screenings_tenant_id", "client_screenings", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_users_api_client_screenings_client_id", "client_screenings", ["client_id"], schema=SCHEMA)

    op.execute(
        """
        INSERT INTO users_api.identification_types (code, name, person_type)
        VALUES
            ('CC', 'Cédula de ciudadanía', 'NATURAL'),
            ('CE', 'Cédula de extranjería', 'NATURAL'),
            ('PASSPORT', 'Pasaporte', 'NATURAL'),
            ('NIT', 'Número de identificación tributaria', 'JURIDICA')
        """
    )
    op.execute(
        """
        INSERT INTO users_api.countries (code, name)
        VALUES ('CO', 'Colombia')
        """
    )

    for table in ("clients", "client_screenings"):
        op.execute(f"ALTER TABLE {SCHEMA}.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {SCHEMA}.{table} FORCE ROW LEVEL SECURITY")

    op.execute(
        f"""
        CREATE POLICY clients_isolation
        ON {SCHEMA}.clients
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY client_screenings_isolation
        ON {SCHEMA}.client_screenings
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS client_screenings_isolation ON users_api.client_screenings")
    op.execute("DROP POLICY IF EXISTS clients_isolation ON users_api.clients")

    for table in ("client_screenings", "clients"):
        op.execute(f"ALTER TABLE users_api.{table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE users_api.{table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_users_api_client_screenings_client_id", table_name="client_screenings", schema=SCHEMA)
    op.drop_index("ix_users_api_client_screenings_tenant_id", table_name="client_screenings", schema=SCHEMA)
    op.drop_table("client_screenings", schema=SCHEMA)

    for index_name, table_name in (
        ("ix_users_api_clients_city_id", "clients"),
        ("ix_users_api_clients_department_id", "clients"),
        ("ix_users_api_clients_country_id", "clients"),
        ("ix_users_api_clients_identification_type_id", "clients"),
        ("ix_users_api_clients_tenant_id", "clients"),
    ):
        op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
    op.drop_table("clients", schema=SCHEMA)

    op.drop_index("ix_users_api_cities_department_id", table_name="cities", schema=SCHEMA)
    op.drop_table("cities", schema=SCHEMA)
    op.drop_index("ix_users_api_departments_country_id", table_name="departments", schema=SCHEMA)
    op.drop_table("departments", schema=SCHEMA)
    op.drop_index("ix_users_api_countries_code", table_name="countries", schema=SCHEMA)
    op.drop_table("countries", schema=SCHEMA)
    op.drop_index("ix_users_api_identification_types_code", table_name="identification_types", schema=SCHEMA)
    op.drop_table("identification_types", schema=SCHEMA)

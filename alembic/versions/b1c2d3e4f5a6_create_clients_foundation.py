"""create clients foundation schema

Revision ID: b1c2d3e4f5a6
Revises: a8b9c0d1e2f3
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(
        """
        CREATE TABLE users_api.clients (
            uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id INTEGER NOT NULL
                REFERENCES users_api.tenants(id) ON DELETE CASCADE,
            client_type VARCHAR(20) NOT NULL DEFAULT 'PERSON',
            id_type VARCHAR(20) NOT NULL,
            id_number VARCHAR(30) NOT NULL,
            first_name VARCHAR(50),
            middle_name VARCHAR(50),
            last_name VARCHAR(50),
            second_last_name VARCHAR(50),
            legal_name VARCHAR(150),
            trade_name VARCHAR(150),
            full_name VARCHAR(150) GENERATED ALWAYS AS (
                CASE
                    WHEN client_type = 'COMPANY' THEN
                        NULLIF(trim(COALESCE(legal_name, trade_name, '')), '')
                    ELSE
                        NULLIF(
                            trim(
                                concat_ws(
                                    ' ',
                                    NULLIF(trim(first_name), ''),
                                    NULLIF(trim(middle_name), ''),
                                    NULLIF(trim(last_name), ''),
                                    NULLIF(trim(second_last_name), '')
                                )
                            ),
                            ''
                        )
                END
            ) STORED,
            birth_date DATE,
            phone VARCHAR(20),
            email VARCHAR(100),
            country_code VARCHAR(3) NOT NULL DEFAULT 'CO',
            department_code VARCHAR(10),
            city_code VARCHAR(10),
            address VARCHAR(200),
            consent_contact BOOLEAN NOT NULL DEFAULT FALSE,
            consent_contact_at TIMESTAMP WITHOUT TIME ZONE,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            compliance_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            is_listed BOOLEAN NOT NULL DEFAULT FALSE,
            list_type VARCHAR(20),
            last_screening_at TIMESTAMP WITHOUT TIME ZONE,
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(100),
            updated_at TIMESTAMP WITHOUT TIME ZONE,

            CONSTRAINT uq_clients_tenant_identification
                UNIQUE (tenant_id, id_type, id_number),
            CONSTRAINT ck_clients_type
                CHECK (client_type IN ('PERSON', 'COMPANY')),
            CONSTRAINT ck_clients_status
                CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')),
            CONSTRAINT ck_clients_compliance_status
                CHECK (compliance_status IN ('PENDING', 'CLEAR', 'MATCH', 'BLOCKED', 'ERROR')),
            CONSTRAINT ck_clients_list_type
                CHECK (list_type IS NULL OR list_type IN ('INFORMATIVE', 'RESTRICTIVE')),
            CONSTRAINT ck_clients_person_company_data
                CHECK (
                    (client_type = 'PERSON' AND first_name IS NOT NULL AND last_name IS NOT NULL)
                    OR
                    (client_type = 'COMPANY' AND legal_name IS NOT NULL)
                ),
            CONSTRAINT ck_clients_consent_contact_at
                CHECK (consent_contact OR consent_contact_at IS NULL)
        )
        """
    )

    op.create_index(
        "ix_clients_tenant_id",
        "clients",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_clients_id_number",
        "clients",
        ["id_number"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_clients_full_name",
        "clients",
        ["full_name"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_clients_compliance_status",
        "clients",
        ["compliance_status"],
        schema=SCHEMA,
    )

    op.execute("ALTER TABLE users_api.clients ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY clients_isolation
        ON users_api.clients
        USING (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        WITH CHECK (
            tenant_id = NULLIF(
                current_setting('app.current_tenant_id', true),
                ''
            )::integer
        )
        """
    )

    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE
        ON TABLE users_api.clients
        TO users_api_app
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS clients_isolation ON users_api.clients")
    op.execute("ALTER TABLE users_api.clients DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_clients_compliance_status", table_name="clients", schema=SCHEMA)
    op.drop_index("ix_clients_full_name", table_name="clients", schema=SCHEMA)
    op.drop_index("ix_clients_id_number", table_name="clients", schema=SCHEMA)
    op.drop_index("ix_clients_tenant_id", table_name="clients", schema=SCHEMA)
    op.drop_table("clients", schema=SCHEMA)

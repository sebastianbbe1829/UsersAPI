"""create extinguisher type catalog

Revision ID: f7a9c2e1b304
Revises: d4e7f1a2b903
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f7a9c2e1b304"
down_revision: Union[str, Sequence[str], None] = "d4e7f1a2b903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"

INITIAL_TYPES = [
    ("POLVO_QUIMICO_SECO", "Polvo químico seco (PQS)"),
    ("CO2", "Dióxido de carbono (CO₂)"),
    ("AGUA", "Agua"),
    ("ESPUMA", "Espuma"),
    ("AGENTE_LIMPIO", "Agente limpio"),
    ("TIPO_K", "Tipo K"),
]


def upgrade() -> None:
    op.create_table(
        "extinguisher_types",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_extinguisher_types_code"),
        schema=SCHEMA,
    )
    op.create_index("ix_users_api_extinguisher_types_code", "extinguisher_types", ["code"], unique=True, schema=SCHEMA)

    for code, name in INITIAL_TYPES:
        op.execute(
            sa.text(
                "INSERT INTO users_api.extinguisher_types (code, name) VALUES (:code, :name)"
            ).bindparams(code=code, name=name)
        )

    op.add_column("extinguishers", sa.Column("extinguisher_type_id_new", sa.Integer(), nullable=True), schema=SCHEMA)
    op.execute(
        sa.text(
            """
            UPDATE users_api.extinguishers e
            SET extinguisher_type_id_new = t.id
            FROM users_api.extinguisher_types t
            WHERE UPPER(TRIM(e.extinguisher_type)) = t.code
            """
        )
    )
    op.alter_column("extinguishers", "extinguisher_type_id_new", nullable=False, schema=SCHEMA)
    op.create_foreign_key(
        "fk_extinguishers_type",
        "extinguishers",
        "extinguisher_types",
        ["extinguisher_type_id_new"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.create_index("ix_users_api_extinguishers_extinguisher_type_id", "extinguishers", ["extinguisher_type_id_new"], schema=SCHEMA)
    op.drop_column("extinguishers", "extinguisher_type", schema=SCHEMA)
    op.alter_column("extinguishers", "extinguisher_type_id_new", new_column_name="extinguisher_type_id", schema=SCHEMA)


def downgrade() -> None:
    op.add_column("extinguishers", sa.Column("extinguisher_type_old", sa.String(length=50), nullable=True), schema=SCHEMA)
    op.execute(
        sa.text(
            """
            UPDATE users_api.extinguishers e
            SET extinguisher_type_old = t.code
            FROM users_api.extinguisher_types t
            WHERE e.extinguisher_type_id = t.id
            """
        )
    )
    op.drop_index("ix_users_api_extinguishers_extinguisher_type_id", table_name="extinguishers", schema=SCHEMA)
    op.drop_constraint("fk_extinguishers_type", "extinguishers", schema=SCHEMA, type_="foreignkey")
    op.drop_column("extinguishers", "extinguisher_type_id", schema=SCHEMA)
    op.alter_column("extinguishers", "extinguisher_type_old", new_column_name="extinguisher_type", nullable=False, schema=SCHEMA)
    op.drop_index("ix_users_api_extinguisher_types_code", table_name="extinguisher_types", schema=SCHEMA)
    op.drop_table("extinguisher_types", schema=SCHEMA)

"""create extinguisher inspection catalog and hydrostatic cycle

Revision ID: 8c4d6e2f1a90
Revises: f7a9c2e1b304
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8c4d6e2f1a90"
down_revision: Union[str, Sequence[str], None] = "f7a9c2e1b304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"
INSPECTIONS = "extinguisher_inspections"
OLD_ITEMS = "extinguisher_inspection_items"
RESULTS = "extinguisher_inspection_results"
CATALOG = "extinguisher_inspection_items"


def upgrade() -> None:
    # The original MVP used this table for inspection detail rows. Preserve it
    # as results and reuse its old name for the new global catalog.
    op.rename_table(OLD_ITEMS, RESULTS, schema=SCHEMA)
    op.execute(
        f"ALTER POLICY extinguisher_inspection_items_isolation ON {SCHEMA}.{RESULTS} "
        "RENAME TO extinguisher_inspection_results_isolation"
    )
    op.execute(
        f"ALTER INDEX {SCHEMA}.ix_users_api_extinguisher_inspection_items_inspection_id "
        "RENAME TO ix_users_api_extinguisher_inspection_results_inspection_id"
    )

    op.add_column("extinguishers", sa.Column("inspections_since_hydrostatic_test", sa.Integer(), nullable=False, server_default=sa.text("0")), schema=SCHEMA)
    op.add_column("extinguishers", sa.Column("inspection_cycle", sa.Integer(), nullable=False, server_default=sa.text("1")), schema=SCHEMA)
    op.add_column(INSPECTIONS, sa.Column("inspection_number", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column(INSPECTIONS, sa.Column("inspection_cycle", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column(INSPECTIONS, sa.Column("hydrostatic_test_performed", sa.Boolean(), nullable=False, server_default=sa.text("false")), schema=SCHEMA)
    op.add_column(INSPECTIONS, sa.Column("hydrostatic_test_date", sa.Date(), nullable=True), schema=SCHEMA)

    op.create_table(
        CATALOG,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_extinguisher_inspection_items_code"),
        schema=SCHEMA,
    )

    seeds = [
        ("MANOMETER", "Manómetro", True, 1),
        ("HANDLE", "Manija", True, 2),
        ("PIN", "Pasador", True, 3),
        ("LABEL", "Etiqueta", True, 4),
        ("PAINT", "Pintura", True, 5),
        ("CYLINDER", "Cilindro", True, 6),
        ("SIGNAGE", "Señalización", True, 7),
        ("LEGACY", "Ítem histórico no catalogado", False, 999),
    ]
    for code, name, active, display_order in seeds:
        op.execute(sa.text(
            f"INSERT INTO {SCHEMA}.{CATALOG} (code, name, active, display_order) "
            "VALUES (:code, :name, :active, :display_order) ON CONFLICT (code) DO NOTHING"
        ).bindparams(code=code, name=name, active=active, display_order=display_order))

    op.add_column(RESULTS, sa.Column("inspection_item_id", sa.Integer(), nullable=True), schema=SCHEMA)
    op.execute(f"""
        UPDATE {SCHEMA}.{RESULTS} r
        SET inspection_item_id = i.id
        FROM {SCHEMA}.{CATALOG} i
        WHERE i.code = CASE UPPER(TRIM(r.item))
            WHEN 'MANOMETRO' THEN 'MANOMETER'
            WHEN 'MANÓMETRO' THEN 'MANOMETER'
            WHEN 'MANIJA' THEN 'HANDLE'
            WHEN 'PASADOR' THEN 'PIN'
            WHEN 'ETIQUETA' THEN 'LABEL'
            WHEN 'PINTURA' THEN 'PAINT'
            WHEN 'CILINDRO' THEN 'CYLINDER'
            WHEN 'SEÑALIZACION' THEN 'SIGNAGE'
            WHEN 'SEÑALIZACIÓN' THEN 'SIGNAGE'
            ELSE 'LEGACY'
        END
    """)
    op.alter_column(RESULTS, "inspection_item_id", nullable=False, schema=SCHEMA)
    op.drop_column(RESULTS, "item", schema=SCHEMA)
    op.create_foreign_key("fk_extinguisher_inspection_results_item", RESULTS, CATALOG, ["inspection_item_id"], ["id"], source_schema=SCHEMA, referent_schema=SCHEMA, ondelete="RESTRICT")
    op.create_index("ix_users_api_extinguisher_inspection_results_item_id", RESULTS, ["inspection_item_id"], unique=False, schema=SCHEMA)

    op.execute(f"""
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY extinguisher_id ORDER BY inspection_date, id) AS rn
            FROM {SCHEMA}.{INSPECTIONS}
        )
        UPDATE {SCHEMA}.{INSPECTIONS} i
        SET inspection_number = ((numbered.rn - 1) % 5) + 1,
            inspection_cycle = ((numbered.rn - 1) / 5) + 1
        FROM numbered
        WHERE i.id = numbered.id
    """)
    op.execute(f"""
        UPDATE {SCHEMA}.extinguishers e
        SET inspections_since_hydrostatic_test = COALESCE(sub.cnt, 0)
        FROM (
            SELECT extinguisher_id, COUNT(*) AS cnt
            FROM {SCHEMA}.{INSPECTIONS}
            WHERE hydrostatic_test_performed = false
            GROUP BY extinguisher_id
        ) sub
        WHERE e.id = sub.extinguisher_id
    """)
    op.alter_column(INSPECTIONS, "inspection_number", nullable=False, schema=SCHEMA)
    op.alter_column(INSPECTIONS, "inspection_cycle", nullable=False, schema=SCHEMA)
    op.create_check_constraint("ck_extinguisher_inspection_number", INSPECTIONS, "inspection_number BETWEEN 1 AND 5", schema=SCHEMA)
    op.create_check_constraint(
        "ck_extinguisher_inspection_hydrostatic_date",
        INSPECTIONS,
        "(hydrostatic_test_performed = false AND hydrostatic_test_date IS NULL) OR (hydrostatic_test_performed = true AND hydrostatic_test_date IS NOT NULL)",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint("ck_extinguisher_inspection_hydrostatic_date", INSPECTIONS, type_="check", schema=SCHEMA)
    op.drop_constraint("ck_extinguisher_inspection_number", INSPECTIONS, type_="check", schema=SCHEMA)
    op.drop_index("ix_users_api_extinguisher_inspection_results_item_id", table_name=RESULTS, schema=SCHEMA)
    op.drop_constraint("fk_extinguisher_inspection_results_item", RESULTS, type_="foreignkey", schema=SCHEMA)
    op.add_column(RESULTS, sa.Column("item", sa.String(length=50), nullable=True), schema=SCHEMA)
    op.execute(f"""
        UPDATE {SCHEMA}.{RESULTS} r
        SET item = i.code
        FROM {SCHEMA}.{CATALOG} i
        WHERE i.id = r.inspection_item_id
    """)
    op.drop_column(RESULTS, "inspection_item_id", schema=SCHEMA)
    op.alter_column(RESULTS, "item", nullable=False, schema=SCHEMA)
    op.drop_table(CATALOG, schema=SCHEMA)
    op.drop_column(INSPECTIONS, "hydrostatic_test_date", schema=SCHEMA)
    op.drop_column(INSPECTIONS, "hydrostatic_test_performed", schema=SCHEMA)
    op.drop_column(INSPECTIONS, "inspection_cycle", schema=SCHEMA)
    op.drop_column(INSPECTIONS, "inspection_number", schema=SCHEMA)
    op.drop_column("extinguishers", "inspection_cycle", schema=SCHEMA)
    op.drop_column("extinguishers", "inspections_since_hydrostatic_test", schema=SCHEMA)
    op.execute(f"ALTER INDEX {SCHEMA}.ix_users_api_extinguisher_inspection_results_inspection_id RENAME TO ix_users_api_extinguisher_inspection_items_inspection_id")
    op.execute(f"ALTER POLICY extinguisher_inspection_results_isolation ON {SCHEMA}.{RESULTS} RENAME TO extinguisher_inspection_items_isolation")
    op.rename_table(RESULTS, OLD_ITEMS, schema=SCHEMA)

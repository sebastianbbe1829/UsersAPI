"""allow historical inspection number zero and ensure Tipo K catalog entry

Revision ID: b9e4f6a1c203
Revises: c3f8a1d6b204, 9d7e8f1a2b30
Create Date: 2026-09-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9e4f6a1c203"
down_revision: Union[str, Sequence[str], None] = ("c3f8a1d6b204", "9d7e8f1a2b30")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "users_api"


def upgrade() -> None:
    # Historical inspections imported without a reliable revision number use
    # revision 0. Preserve the existing 1..5 validation for normal inspections
    # while explicitly allowing the migration-only value 0.
    op.drop_constraint(
        "ck_extinguisher_inspection_number",
        "extinguisher_inspections",
        type_="check",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_extinguisher_inspection_number",
        "extinguisher_inspections",
        "inspection_number BETWEEN 0 AND 5",
        schema=SCHEMA,
    )

    # Existing databases may have already applied the catalog migration before
    # TIPO_K was added to its seed list. Insert it only when it is missing.
    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.extinguisher_types (code, name)
            SELECT :code, :name
            WHERE NOT EXISTS (
                SELECT 1
                FROM {SCHEMA}.extinguisher_types
                WHERE code = :code
            )
            """
        ).bindparams(code="TIPO_K", name="Tipo K")
    )


def downgrade() -> None:
    # A downgrade is only valid when no migration-created inspection uses 0.
    # Do not silently change historical data to another revision number.
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.extinguisher_inspections
                    WHERE inspection_number = 0
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade: extinguisher inspections with inspection_number = 0 exist';
                END IF;
            END $$;
            """
        )
    )

    op.drop_constraint(
        "ck_extinguisher_inspection_number",
        "extinguisher_inspections",
        type_="check",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_extinguisher_inspection_number",
        "extinguisher_inspections",
        "inspection_number BETWEEN 1 AND 5",
        schema=SCHEMA,
    )

    op.execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.extinguisher_types WHERE code = :code"
        ).bindparams(code="TIPO_K")
    )

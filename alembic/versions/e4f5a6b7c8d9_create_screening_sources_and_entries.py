"""create official screening source catalog

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "screening_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default=sa.text("'OFFICIAL'")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_status", sa.String(length=20), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="users_api",
    )

    op.create_table(
        "screening_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=150), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("normalized_name", sa.String(length=300), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("identification_numbers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("nationality", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["users_api.screening_sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_screening_entries_source_external_id"),
        schema="users_api",
    )
    op.create_index("ix_screening_entries_source_id", "screening_entries", ["source_id"], schema="users_api")
    op.create_index("ix_screening_entries_name", "screening_entries", ["name"], schema="users_api")
    op.create_index("ix_screening_entries_normalized_name", "screening_entries", ["normalized_name"], schema="users_api")

    screening_sources = sa.table(
        "screening_sources",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("provider", sa.String()),
        sa.column("url", sa.Text()),
        schema="users_api",
    )
    op.bulk_insert(
        screening_sources,
        [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "code": "OFAC_SDN",
                "name": "OFAC Specially Designated Nationals",
                "provider": "OFAC",
                "url": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML",
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "code": "OFAC_CONSOLIDATED",
                "name": "OFAC Consolidated Sanctions List",
                "provider": "OFAC",
                "url": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML",
            },
            {
                "id": "00000000-0000-0000-0000-000000000003",
                "code": "UN_CONSOLIDATED",
                "name": "United Nations Security Council Consolidated List",
                "provider": "UN",
                "url": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_screening_entries_normalized_name", table_name="screening_entries", schema="users_api")
    op.drop_index("ix_screening_entries_name", table_name="screening_entries", schema="users_api")
    op.drop_index("ix_screening_entries_source_id", table_name="screening_entries", schema="users_api")
    op.drop_table("screening_entries", schema="users_api")
    op.drop_table("screening_sources", schema="users_api")

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ScreeningEntryDB(Base):
    __tablename__ = "screening_entries"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "external_id",
            name="uq_screening_entries_source_external_id",
        ),
        Index("ix_screening_entries_source_id", "source_id"),
        Index("ix_screening_entries_name", "name"),
        Index("ix_screening_entries_normalized_name", "normalized_name"),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.screening_sources.id"),
        nullable=False,
    )
    external_id = Column(String(100), nullable=False)
    entry_type = Column(String(30), nullable=True)
    name = Column(String(300), nullable=False)
    normalized_name = Column(String(300), nullable=False)
    aliases = Column(JSONB, nullable=True)
    identification_numbers = Column(JSONB, nullable=True)
    nationality = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    raw_data = Column(JSONB, nullable=True)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    source = relationship("ScreeningSourceDB", back_populates="entries")

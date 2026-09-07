import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ScreeningSourceDB(Base):
    __tablename__ = "screening_sources"
    __table_args__ = {"schema": "users_api"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(150), nullable=False)
    provider = Column(String(50), nullable=False, server_default=text("'OFFICIAL'"))
    url = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), nullable=True)
    last_sync_error = Column(Text, nullable=True)

    entries = relationship("ScreeningEntryDB", back_populates="source")

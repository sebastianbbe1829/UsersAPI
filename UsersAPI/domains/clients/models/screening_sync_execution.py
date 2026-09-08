import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from UsersAPI.domains.core.database import Base


class ScreeningSyncExecutionDB(Base):
    __tablename__ = "screening_sync_executions"
    __table_args__ = {"schema": "users_api"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type = Column(String(20), nullable=False)
    triggered_by = Column(Integer, nullable=True)
    triggered_by_email = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, server_default="PENDING")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    total_sources = Column(Integer, nullable=True)
    successful_sources = Column(Integer, nullable=True)
    failed_sources = Column(Integer, nullable=True)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

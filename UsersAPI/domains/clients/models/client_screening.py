import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ClientScreeningDB(Base):
    __tablename__ = "client_screenings"
    __table_args__ = {"schema": "users_api"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id"), nullable=False, index=True)
    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_api.clients.id"),
        nullable=False,
        index=True,
    )

    provider = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'PENDING'"))
    risk_level = Column(String(20), nullable=True)
    matched = Column(Boolean, nullable=False, server_default=text("false"))
    requested_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    completed_at = Column(DateTime, nullable=True)
    response = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    client = relationship("ClientDB", back_populates="screenings")

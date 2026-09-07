import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ClientComplianceOverrideDB(Base):
    __tablename__ = "client_compliance_overrides"
    __table_args__ = {"schema": "users_api"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users_api.clients.id"), nullable=False, index=True)
    screening_id = Column(UUID(as_uuid=True), ForeignKey("users_api.client_screenings.id"), nullable=True, index=True)
    requested_by = Column(Integer, nullable=False)
    requested_by_email = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    mfa_verified_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    client = relationship("ClientDB", back_populates="compliance_overrides")
    screening = relationship("ClientScreeningDB")

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class ClientDB(Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_tenant_identification", "tenant_id", "id_type", "id_number"),
        {"schema": "users_api"},
    )

    uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_type = Column(String(20), nullable=False, default="PERSON", server_default=text("'PERSON'"))
    id_type = Column(String(20), nullable=False)
    id_number = Column(String(30), nullable=False, index=True)
    first_name = Column(String(50), nullable=True)
    middle_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    second_last_name = Column(String(50), nullable=True)
    legal_name = Column(String(150), nullable=True)
    trade_name = Column(String(150), nullable=True)
    full_name = Column(String(150), nullable=True)
    birth_date = Column(Date, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    country_code = Column(String(3), nullable=False, default="CO", server_default=text("'CO'"))
    department_code = Column(String(10), nullable=True)
    city_code = Column(String(10), nullable=True)
    address = Column(String(200), nullable=True)
    consent_contact = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    consent_contact_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'"))
    compliance_status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default=text("'PENDING'"),
    )
    is_listed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    list_type = Column(String(20), nullable=True)
    last_screening_at = Column(DateTime, nullable=True)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, nullable=True)

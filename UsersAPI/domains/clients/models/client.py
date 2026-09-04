import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from UsersAPI.domains.core.database import Base


class ClientDB(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "identification_type_id",
            "identification_number",
            name="uq_clients_tenant_identification",
        ),
        {"schema": "users_api"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id"), nullable=False, index=True)

    identification_type_id = Column(
        Integer,
        ForeignKey("users_api.identification_types.id"),
        nullable=False,
        index=True,
    )
    identification_number = Column(String(50), nullable=False)

    person_type = Column(String(20), nullable=False)
    first_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    second_last_name = Column(String(100), nullable=True)
    business_name = Column(String(250), nullable=True)
    full_name = Column(String(250), nullable=False)

    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(250), nullable=True)

    country_id = Column(
        Integer,
        ForeignKey("users_api.countries.id"),
        nullable=True,
        index=True,
    )
    department_id = Column(
        Integer,
        ForeignKey("users_api.departments.id"),
        nullable=True,
        index=True,
    )
    city_id = Column(
        Integer,
        ForeignKey("users_api.cities.id"),
        nullable=True,
        index=True,
    )

    status = Column(String(20), nullable=False, server_default=text("'ACTIVE'"))
    compliance_status = Column(
        String(20), nullable=False, server_default=text("'PENDING'")
    )

    is_listed = Column(Boolean, nullable=False, server_default=text("false"))
    list_type = Column(String(50), nullable=True)

    consent_given = Column(Boolean, nullable=False, server_default=text("false"))
    consent_at = Column(DateTime, nullable=True)
    consent_source = Column(String(100), nullable=True)

    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)

    identification_type = relationship("IdentificationTypeDB", back_populates="clients")
    country = relationship("CountryDB", back_populates="clients")
    department = relationship("DepartmentDB", back_populates="clients")
    city = relationship("CityDB", back_populates="clients")
    screenings = relationship(
        "ClientScreeningDB",
        back_populates="client",
        cascade="all, delete-orphan",
    )

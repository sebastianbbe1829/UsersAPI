from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Identity, Integer, String, Text, text
from sqlalchemy.orm import relationship

from ..database import Base


class ExtinguisherInspectionItemDB(Base):
    __tablename__ = "extinguisher_inspection_items"
    __table_args__ = {"schema": "users_api"}

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    display_order = Column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=True)


class ExtinguisherInspectionDB(Base):
    __tablename__ = "extinguisher_inspections"
    __table_args__ = {"schema": "users_api"}

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("users_api.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    extinguisher_id = Column(Integer, ForeignKey("users_api.extinguishers.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_date = Column(Date, nullable=False)
    inspector_user_id = Column(Integer, ForeignKey("users_api.user_tenants.id"), nullable=True)
    inspection_number = Column(Integer, nullable=False)
    inspection_cycle = Column(Integer, nullable=False)
    result = Column(String(30), nullable=False)
    observations = Column(Text, nullable=True)
    hydrostatic_test_performed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    hydrostatic_test_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    results = relationship(
        "ExtinguisherInspectionResultDB",
        back_populates="inspection",
        cascade="all, delete-orphan",
        order_by="ExtinguisherInspectionResultDB.id",
    )


class ExtinguisherInspectionResultDB(Base):
    __tablename__ = "extinguisher_inspection_results"
    __table_args__ = {"schema": "users_api"}

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    inspection_id = Column(Integer, ForeignKey("users_api.extinguisher_inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_item_id = Column(Integer, ForeignKey("users_api.extinguisher_inspection_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    result = Column(String(30), nullable=False)
    observation = Column(Text, nullable=True)

    inspection = relationship("ExtinguisherInspectionDB", back_populates="results")
    inspection_item = relationship("ExtinguisherInspectionItemDB")

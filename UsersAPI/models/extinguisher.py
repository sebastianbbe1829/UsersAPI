from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import relationship

from ..database import Base


class ExtinguisherDB(Base):
    __tablename__ = "extinguishers"
    __table_args__ = {"schema": "users_api"}

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(50), nullable=False, index=True)
    extinguisher_type_id = Column(
        Integer,
        ForeignKey("users_api.extinguisher_types.id"),
        nullable=False,
        index=True,
    )
    capacity = Column(String(30), nullable=True)
    location = Column(String(150), nullable=True)
    last_recharge_date = Column(Date, nullable=True)
    next_recharge_date = Column(Date, nullable=True)
    last_hydrostatic_test_date = Column(Date, nullable=True)
    next_hydrostatic_test_date = Column(Date, nullable=True)
    inspections_since_hydrostatic_test = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    inspection_cycle = Column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    status = Column(String(30), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'"))
    is_stock = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=True)

    extinguisher_type = relationship("ExtinguisherTypeDB")

    @property
    def hydrostatic_test_required(self) -> bool:
        return self.inspections_since_hydrostatic_test >= 4

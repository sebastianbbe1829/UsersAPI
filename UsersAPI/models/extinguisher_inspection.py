from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    text,
)

from ..database import Base


class ExtinguisherInspectionDB(Base):

    __tablename__ = "extinguisher_inspections"

    __table_args__ = (
        {
            "schema": "users_api"
        },
    )

    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )

    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    extinguisher_id = Column(
        Integer,
        ForeignKey("users_api.extinguishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    inspection_date = Column(
        Date,
        nullable=False,
    )

    inspector_user_id = Column(
        Integer,
        ForeignKey("users_api.user_tenants.id"),
        nullable=True,
    )

    result = Column(
        String(30),
        nullable=False,
    )

    observations = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ExtinguisherInspectionItemDB(Base):

    __tablename__ = "extinguisher_inspection_items"

    __table_args__ = (
        {
            "schema": "users_api"
        },
    )

    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )

    inspection_id = Column(
        Integer,
        ForeignKey("users_api.extinguisher_inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    item = Column(
        String(50),
        nullable=False,
    )

    result = Column(
        String(30),
        nullable=False,
    )

    observation = Column(
        Text,
        nullable=True,
    )

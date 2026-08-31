from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Text,
    text,
)

from ..database import Base


class ExtinguisherRechargeDB(Base):

    __tablename__ = "extinguisher_recharges"

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

    recharge_date = Column(
        Date,
        nullable=False,
    )

    next_due_date = Column(
        Date,
        nullable=True,
    )

    observations = Column(
        Text,
        nullable=True,
    )

    created_by = Column(
        Integer,
        ForeignKey("users_api.user_tenants.id"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

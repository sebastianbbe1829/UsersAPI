from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    text,
    Identity,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from ..database import Base


class TenantDB(Base):

    __tablename__ = "tenants"

    __table_args__ = (
        UniqueConstraint(
            "slug",
            name="uq_tenants_slug",
        ),
        {
            "schema": "users_api"
        },
    )

    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )

    name = Column(
        String(150),
        nullable=False,
        index=True,
    )

    slug = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    status = Column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    created_by = Column(
        String(100),
        nullable=False,
    )

    created_by_bd = Column(
        String(100),
        nullable=True,
        server_default=text("USER"),
    )

    updated_at = Column(
        DateTime,
        nullable=True,
    )

    updated_by = Column(
        String(100),
        nullable=True,
    )

    updated_by_bd = Column(
        String(100),
        nullable=True,
        server_default=text("USER"),
    )

    users = relationship(
        "UserTenantDB",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    roles = relationship(
        "RoleDB",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    config = relationship(
        "TenantConfigDB",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )

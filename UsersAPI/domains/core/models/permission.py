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


class PermissionDB(Base):

    __tablename__ = "permissions"

    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_permissions_code",
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

    code = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(
        String(150),
        nullable=False,
    )

    description = Column(
        String(255),
        nullable=True,
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

    roles = relationship(
        "RolePermissionDB",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
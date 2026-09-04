from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy import Identity
from sqlalchemy.orm import relationship

from ..database import Base


class UserDB(Base):

    __tablename__ = "app_users"

    __table_args__ = {
        "schema": "users_api"
    }

    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )

    # Información del usuario
    dni = Column(
        String(20),
        nullable=False,
        index=True,
    )

    name = Column(
        String(100),
        nullable=False,
        index=True,
    )


    # Auditoría creación
    created_at = Column(
        DateTime,
        nullable=False,
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


    # Auditoría actualización
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


    tenants = relationship(
        "UserTenantDB",
        back_populates="user",
        cascade="all, delete-orphan",
    )
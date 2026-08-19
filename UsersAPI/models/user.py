from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy import Identity

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

    dni = Column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(
        String(100),
        index=True,
    )

    email = Column(
        String(255),
        unique=True,
        index=True,
    )

    status = Column(
        Integer,
        default=0,
    )

    phone = Column(
        String(20),
        nullable=True,
    )

    password = Column(
        String(200),
        nullable=False,
    )

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

    activation_token = Column(
        String(200),
        unique=True,
        index=True,
    )
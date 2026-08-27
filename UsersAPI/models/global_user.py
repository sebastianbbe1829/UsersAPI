from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy import Identity

from ..database import Base


class GlobalUserDB(Base):

    __tablename__ = "global_users"

    __table_args__ = {
        "schema": "users_api"
    }

    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )

    email = Column(
        String(255),
        nullable=False,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    is_superuser = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    mfa_enabled = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    mfa_secret_encrypted = Column(
        String(512),
        nullable=True,
    )

    mfa_verified_at = Column(
        DateTime,
        nullable=True,
    )

    session_id = Column(
        String(36),
        nullable=True,
        unique=True,
        index=True,
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
    )

    last_login_ip = Column(
        String(45),
        nullable=True,
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
    )

    created_by_bd = Column(
        String(100),
        nullable=True,
        server_default=text("USER"),
    )

    updated_by_bd = Column(
        String(100),
        nullable=True,
        server_default=text("USER"),
    )

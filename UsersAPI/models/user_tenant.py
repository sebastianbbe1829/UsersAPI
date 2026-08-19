from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
    Identity,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from ..database import Base


class UserTenantDB(Base):

    __tablename__ = "user_tenants"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_user_tenants_user_tenant",
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

    user_id = Column(
        Integer,
        ForeignKey(
            "users_api.app_users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    tenant_id = Column(
        Integer,
        ForeignKey(
            "users_api.tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
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

    user = relationship(
        "UserDB",
        back_populates="tenants",
    )

    tenant = relationship(
        "TenantDB",
        back_populates="users",
    )
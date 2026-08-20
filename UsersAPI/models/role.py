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


class RoleDB(Base):

    __tablename__ = "roles"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_roles_tenant_code",
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

    tenant_id = Column(
        Integer,
        ForeignKey(
            "users_api.tenants.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    code = Column(
        String(50),
        nullable=False,
        index=True,
    )

    name = Column(
        String(100),
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

    tenant = relationship(
        "TenantDB",
        back_populates="roles",
    )

    permissions = relationship(
        "RolePermissionDB",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    user_tenant_roles = relationship(
        "UserTenantRoleDB",
        back_populates="role",
        cascade="all, delete-orphan",
    )
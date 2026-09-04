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
        UniqueConstraint(
            "tenant_id",
            "email",
            name="uq_user_tenants_tenant_email",
        ),
        {"schema": "users_api"},
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users_api.app_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email = Column(String(255), nullable=False, index=True)
    password = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=True)
    activation_token = Column(String(200), nullable=True, unique=True, index=True)

    # 0 = inactivo, 1 = activo, 3 = eliminado
    status = Column(Integer, nullable=False, default=1, server_default=text("1"))

    # Seguridad de autenticación: independiente por tenant.
    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_failed_login_at = Column(DateTime, nullable=True)
    locked_at = Column(DateTime, nullable=True)
    locked_ip = Column(String(45), nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    created_by = Column(String(100), nullable=False)
    created_by_bd = Column(String(100), nullable=True, server_default=text("USER"))
    updated_at = Column(DateTime, nullable=True)
    updated_by = Column(String(100), nullable=True)
    updated_by_bd = Column(String(100), nullable=True, server_default=text("USER"))

    user = relationship("UserDB", back_populates="tenants")
    tenant = relationship("TenantDB", back_populates="users")
    roles = relationship(
        "UserTenantRoleDB",
        back_populates="user_tenant",
        cascade="all, delete-orphan",
    )

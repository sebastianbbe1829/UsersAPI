from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from ..database import Base


class UserTenantRoleDB(Base):

    __tablename__ = "user_tenant_roles"

    __table_args__ = (
        UniqueConstraint(
            "user_tenant_id",
            "role_id",
            name="uq_user_tenant_roles_user_tenant_role",
        ),
        {
            "schema": "users_api"
        },
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_tenant_id = Column(
        Integer,
        ForeignKey(
            "users_api.user_tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role_id = Column(
        Integer,
        ForeignKey(
            "users_api.roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_tenant = relationship(
        "UserTenantDB",
        back_populates="roles",
    )

    role = relationship(
        "RoleDB",
        back_populates="user_tenant_roles",
    )
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from ..database import Base


class RolePermissionDB(Base):

    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
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

    role_id = Column(
        Integer,
        ForeignKey(
            "users_api.roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    permission_id = Column(
        Integer,
        ForeignKey(
            "users_api.permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role = relationship(
        "RoleDB",
        back_populates="permissions",
    )

    permission = relationship(
        "PermissionDB",
        back_populates="roles",
    )
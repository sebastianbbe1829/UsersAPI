from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from ..database import Base


class TenantConfigDB(Base):

    __tablename__ = "tenant_configs"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            name="uq_tenant_configs_tenant_id",
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

    tenant_id = Column(
        Integer,
        ForeignKey(
            "users_api.tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    app_title = Column(
        String(150),
        nullable=False,
    )

    logo_url = Column(
        String(500),
        nullable=True,
    )

    primary_color = Column(
        String(7),
        nullable=False,
        server_default=text("'#0D6EFD'"),
    )

    secondary_color = Column(
        String(7),
        nullable=False,
        server_default=text("'#6C757D'"),
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

    updated_at = Column(
        DateTime,
        nullable=True,
    )

    updated_by = Column(
        String(100),
        nullable=True,
    )

    tenant = relationship(
        "TenantDB",
        back_populates="config",
    )

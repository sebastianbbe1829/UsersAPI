from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, text

from ..database import Base


class AuthSessionDB(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_users_api_auth_sessions_tenant_id", "tenant_id"),
        Index("ix_users_api_auth_sessions_user_tenant_id", "user_tenant_id"),
        Index("ix_users_api_auth_sessions_global_user_id", "global_user_id"),
        {"schema": "users_api"},
    )

    id = Column(String(36), primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_tenant_id = Column(
        Integer,
        ForeignKey("users_api.user_tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    global_user_id = Column(
        Integer,
        ForeignKey("users_api.global_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_kind = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    login_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    logout_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(1000), nullable=True)
    status = Column(String(20), nullable=False, server_default=text("'ACTIVE'"))


class AuthAuditDB(Base):
    __tablename__ = "auth_audit"
    __table_args__ = (
        Index("ix_users_api_auth_audit_tenant_id", "tenant_id"),
        Index("ix_users_api_auth_audit_occurred_at", "occurred_at"),
        Index("ix_users_api_auth_audit_session_id", "session_id"),
        {"schema": "users_api"},
    )

    id = Column(String(36), primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_tenant_id = Column(
        Integer,
        ForeignKey("users_api.user_tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    global_user_id = Column(
        Integer,
        ForeignKey("users_api.global_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id = Column(String(36), nullable=True)
    session_kind = Column(String(20), nullable=False)
    event_type = Column(String(30), nullable=False)
    actor_identifier = Column(String(255), nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(1000), nullable=True)
    occurred_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

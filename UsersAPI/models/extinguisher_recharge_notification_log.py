from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String

from ..database import Base


class ExtinguisherRechargeNotificationLogDB(Base):
    """Registro persistente de notificaciones de recarga por tenant."""

    __tablename__ = "extinguisher_recharge_notification_log"
    __table_args__ = {"schema": "users_api"}

    notification_date = Column(Date, primary_key=True, nullable=False)
    tenant_id = Column(
        Integer,
        ForeignKey("users_api.tenants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    recipient = Column(String(320), primary_key=True, nullable=False)
    status = Column(String(20), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

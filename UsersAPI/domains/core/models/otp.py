from sqlalchemy import Column, DateTime, Identity, Index, Integer, String, text

from ..database import Base


class OTPCodeDB(Base):
    """Código OTP temporal reutilizable por diferentes flujos del sistema."""

    __tablename__ = "otp_codes"
    __table_args__ = (
        Index("ix_otp_codes_purpose_destination", "purpose", "destination"),
        Index("ix_otp_codes_expires_at", "expires_at"),
        {"schema": "users_api"},
    )

    id = Column(
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )

    purpose = Column(String(50), nullable=False, index=True)
    destination = Column(String(320), nullable=False)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, nullable=False, default=0, server_default=text("0"))
    max_attempts = Column(Integer, nullable=False, default=5, server_default=text("5"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

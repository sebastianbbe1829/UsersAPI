import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models.otp import OTPCodeDB
from ..repositories.otp_repository import OTPRepository
from ..settings import settings
from ..util.email_utils import send_email


def _normalize_destination(destination: str) -> str:
    return destination.strip().lower()


def _hash_code(code: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_otp(
    db: Session,
    *,
    destination: str,
    purpose: str,
) -> datetime:
    """Genera y envía un OTP. La transacción la gestiona get_db()."""
    destination = _normalize_destination(destination)
    purpose = purpose.strip().lower()

    if not destination:
        raise ValueError("destination es obligatorio")
    if not purpose:
        raise ValueError("purpose es obligatorio")

    repository = OTPRepository(db)
    now = datetime.utcnow()

    previous_codes = repository.get_active_all(destination, purpose)
    for previous in previous_codes:
        previous.consumed_at = now
        repository.update(previous)

    code = f"{secrets.randbelow(10 ** settings.otp_length):0{settings.otp_length}d}"
    expires_at = now + timedelta(minutes=settings.otp_expire_minutes)

    otp = OTPCodeDB(
        purpose=purpose,
        destination=destination,
        code_hash=_hash_code(code),
        expires_at=expires_at,
        max_attempts=settings.otp_max_attempts,
    )
    repository.add(otp)

    send_email(
        recipient=destination,
        subject="Código de verificación OTP",
        message="Hemos generado un código de verificación para tu solicitud.",
        template="otp",
        otp_code=code,
        otp_expire_minutes=settings.otp_expire_minutes,
    )

    return expires_at


def validate_otp(
    db: Session,
    *,
    destination: str,
    purpose: str,
    code: str,
) -> bool:
    """Valida un OTP. La transacción la gestiona get_db()."""
    destination = _normalize_destination(destination)
    purpose = purpose.strip().lower()
    code = code.strip()

    repository = OTPRepository(db)
    otp = repository.get_active(destination, purpose)

    if not otp:
        return False

    now = datetime.utcnow()

    if otp.expires_at <= now or otp.attempts >= otp.max_attempts:
        return False

    otp.attempts += 1

    valid = hmac.compare_digest(
        otp.code_hash,
        _hash_code(code),
    )

    if valid:
        otp.consumed_at = now

    repository.update(otp)
    return valid

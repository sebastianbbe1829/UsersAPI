import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models.otp import OTPCodeDB
from ..settings import settings


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
) -> tuple[OTPCodeDB, str]:
    """Genera un OTP y deja inválidos los OTP anteriores del mismo flujo."""
    destination = _normalize_destination(destination)
    purpose = purpose.strip().lower()

    if not destination:
        raise ValueError("destination es obligatorio")
    if not purpose:
        raise ValueError("purpose es obligatorio")

    now = datetime.utcnow()

    previous_codes = (
        db.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == destination,
            OTPCodeDB.purpose == purpose,
            OTPCodeDB.consumed_at.is_(None),
        )
        .all()
    )

    for previous in previous_codes:
        previous.consumed_at = now

    code = f"{secrets.randbelow(10 ** settings.otp_length):0{settings.otp_length}d}"

    otp = OTPCodeDB(
        purpose=purpose,
        destination=destination,
        code_hash=_hash_code(code),
        expires_at=now + timedelta(minutes=settings.otp_expire_minutes),
        max_attempts=settings.otp_max_attempts,
    )

    db.add(otp)
    db.flush()

    return otp, code


def validate_otp(
    db: Session,
    *,
    destination: str,
    purpose: str,
    code: str,
) -> bool:
    """Valida un OTP sin revelar si falló por código, expiración o consumo."""
    destination = _normalize_destination(destination)
    purpose = purpose.strip().lower()
    code = code.strip()

    otp = (
        db.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == destination,
            OTPCodeDB.purpose == purpose,
            OTPCodeDB.consumed_at.is_(None),
        )
        .order_by(OTPCodeDB.created_at.desc(), OTPCodeDB.id.desc())
        .first()
    )

    if not otp:
        return False

    now = datetime.utcnow()

    if otp.expires_at <= now or otp.attempts >= otp.max_attempts:
        db.commit()
        return False

    otp.attempts += 1

    valid = hmac.compare_digest(
        otp.code_hash,
        _hash_code(code),
    )

    if valid:
        otp.consumed_at = now

    db.commit()
    return valid

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.models.otp import OTPCodeDB
from UsersAPI.services.otp_service import _hash_code, generate_otp, validate_otp


def unique_destination() -> str:
    return f"otp-{uuid4().hex}@example.com"


def test_generate_otp_normalizes_destination_and_purpose_and_sends_code(
    db_session: Session,
    monkeypatch,
):
    sent = {}
    destination = unique_destination()
    raw_destination = f"  {destination.upper()} "
    expected_destination = destination.lower()

    def fake_send_email(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr("UsersAPI.services.otp_service.send_email", fake_send_email)

    expires_at = generate_otp(
        db_session,
        destination=raw_destination,
        purpose=" PASSWORD_RECOVERY ",
    )

    otp = (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == expected_destination,
            OTPCodeDB.purpose == "password_recovery",
        )
        .one()
    )

    assert otp.destination == expected_destination
    assert otp.purpose == "password_recovery"
    assert otp.code_hash == _hash_code(sent["otp_code"])
    assert otp.expires_at == expires_at
    assert otp.consumed_at is None
    assert sent["template"] == "otp"


def test_generate_otp_invalidates_previous_active_code(
    db_session: Session,
    monkeypatch,
):
    sent_codes = []
    destination = unique_destination()

    def fake_send_email(**kwargs):
        sent_codes.append(kwargs["otp_code"])

    monkeypatch.setattr("UsersAPI.services.otp_service.send_email", fake_send_email)

    generate_otp(
        db_session,
        destination=destination,
        purpose="login",
    )
    first = (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == destination,
            OTPCodeDB.purpose == "login",
        )
        .one()
    )

    generate_otp(
        db_session,
        destination=destination,
        purpose="login",
    )

    codes = (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == destination,
            OTPCodeDB.purpose == "login",
        )
        .order_by(OTPCodeDB.id)
        .all()
    )

    assert len(codes) == 2
    assert codes[0].consumed_at is not None
    assert codes[1].consumed_at is None
    assert codes[1].code_hash == _hash_code(sent_codes[1])
    assert first.id == codes[0].id


def test_validate_otp_accepts_valid_code_and_consumes_it(
    db_session: Session,
    monkeypatch,
):
    sent = {}
    destination = unique_destination()
    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    generate_otp(
        db_session,
        destination=destination,
        purpose="account_activation",
    )

    assert validate_otp(
        db_session,
        destination=destination.upper(),
        purpose="ACCOUNT_ACTIVATION",
        code=sent["otp_code"],
    ) is True

    otp = (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == destination,
            OTPCodeDB.purpose == "account_activation",
        )
        .one()
    )
    assert otp.attempts == 1
    assert otp.consumed_at is not None

    assert validate_otp(
        db_session,
        destination=destination,
        purpose="account_activation",
        code=sent["otp_code"],
    ) is False


def test_validate_otp_rejects_invalid_code_and_increments_attempts(
    db_session: Session,
    monkeypatch,
):
    destination = unique_destination()
    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: None,
    )

    generate_otp(
        db_session,
        destination=destination,
        purpose="login",
    )

    assert validate_otp(
        db_session,
        destination=destination,
        purpose="login",
        code="000000",
    ) is False

    otp = (
        db_session.query(OTPCodeDB)
        .filter(
            OTPCodeDB.destination == destination,
            OTPCodeDB.purpose == "login",
        )
        .one()
    )
    assert otp.attempts == 1
    assert otp.consumed_at is None


def test_validate_otp_rejects_expired_code_without_incrementing_attempts(
    db_session: Session,
):
    destination = unique_destination()
    otp = OTPCodeDB(
        destination=destination,
        purpose="login",
        code_hash=_hash_code("123456"),
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        max_attempts=5,
    )
    db_session.add(otp)
    db_session.flush()

    assert validate_otp(
        db_session,
        destination=destination,
        purpose="login",
        code="123456",
    ) is False
    assert otp.attempts == 0


def test_validate_otp_rejects_code_after_max_attempts(
    db_session: Session,
):
    destination = unique_destination()
    otp = OTPCodeDB(
        destination=destination,
        purpose="login",
        code_hash=_hash_code("123456"),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        attempts=5,
        max_attempts=5,
    )
    db_session.add(otp)
    db_session.flush()

    assert validate_otp(
        db_session,
        destination=destination,
        purpose="login",
        code="123456",
    ) is False
    assert otp.attempts == 5


def test_validate_otp_returns_false_when_no_active_code_exists(
    db_session: Session,
):
    destination = unique_destination()
    assert validate_otp(
        db_session,
        destination=destination,
        purpose="login",
        code="123456",
    ) is False


def test_otp_routes_require_api_key(
    client: TestClient,
):
    response = client.post(
        "/otp/validate",
        json={
            "destination": "user@example.com",
            "purpose": "login",
            "code": "123456",
        },
    )

    assert response.status_code == 422

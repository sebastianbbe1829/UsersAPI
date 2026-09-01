from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.models.otp import OTPCodeDB
from UsersAPI.services.otp_service import _hash_code, generate_otp, validate_otp


def test_generate_otp_normalizes_destination_and_purpose_and_sends_code(
    db_session: Session,
    monkeypatch,
):
    sent = {}

    def fake_send_email(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr("UsersAPI.services.otp_service.send_email", fake_send_email)

    expires_at = generate_otp(
        db_session,
        destination="  USER@Example.COM ",
        purpose=" PASSWORD_RECOVERY ",
    )

    otp = db_session.query(OTPCodeDB).one()

    assert otp.destination == "user@example.com"
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

    def fake_send_email(**kwargs):
        sent_codes.append(kwargs["otp_code"])

    monkeypatch.setattr("UsersAPI.services.otp_service.send_email", fake_send_email)

    generate_otp(
        db_session,
        destination="user@example.com",
        purpose="login",
    )
    first = db_session.query(OTPCodeDB).one()

    generate_otp(
        db_session,
        destination="user@example.com",
        purpose="login",
    )

    codes = (
        db_session.query(OTPCodeDB)
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
    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: sent.update(kwargs),
    )

    generate_otp(
        db_session,
        destination="user@example.com",
        purpose="account_activation",
    )

    assert validate_otp(
        db_session,
        destination="USER@EXAMPLE.COM",
        purpose="ACCOUNT_ACTIVATION",
        code=sent["otp_code"],
    ) is True

    otp = db_session.query(OTPCodeDB).one()
    assert otp.attempts == 1
    assert otp.consumed_at is not None

    assert validate_otp(
        db_session,
        destination="user@example.com",
        purpose="account_activation",
        code=sent["otp_code"],
    ) is False


def test_validate_otp_rejects_invalid_code_and_increments_attempts(
    db_session: Session,
    monkeypatch,
):
    monkeypatch.setattr(
        "UsersAPI.services.otp_service.send_email",
        lambda **kwargs: None,
    )

    generate_otp(
        db_session,
        destination="user@example.com",
        purpose="login",
    )

    assert validate_otp(
        db_session,
        destination="user@example.com",
        purpose="login",
        code="000000",
    ) is False

    otp = db_session.query(OTPCodeDB).one()
    assert otp.attempts == 1
    assert otp.consumed_at is None


def test_validate_otp_rejects_expired_code_without_incrementing_attempts(
    db_session: Session,
):
    otp = OTPCodeDB(
        destination="user@example.com",
        purpose="login",
        code_hash=_hash_code("123456"),
        expires_at=datetime.utcnow() - timedelta(minutes=1),
        max_attempts=5,
    )
    db_session.add(otp)
    db_session.flush()

    assert validate_otp(
        db_session,
        destination="user@example.com",
        purpose="login",
        code="123456",
    ) is False
    assert otp.attempts == 0


def test_validate_otp_rejects_code_after_max_attempts(
    db_session: Session,
):
    otp = OTPCodeDB(
        destination="user@example.com",
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
        destination="user@example.com",
        purpose="login",
        code="123456",
    ) is False
    assert otp.attempts == 5


def test_validate_otp_returns_false_when_no_active_code_exists(
    db_session: Session,
):
    assert validate_otp(
        db_session,
        destination="user@example.com",
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

    assert response.status_code in (401, 403)

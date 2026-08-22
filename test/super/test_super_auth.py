from datetime import datetime, timezone

import pyotp
import pytest
from fastapi import HTTPException

from UsersAPI.database import SessionLocal
from UsersAPI.models import GlobalUserDB
from UsersAPI.services.auth_service import get_password_hash
from UsersAPI.services.global_auth_service import (
    _create_super_token,
    _encrypt_mfa_secret,
    get_current_super_user,
    login_super_user,
)
from UsersAPI.schemas.global_auth import SuperLoginRequest


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def temporary_super(db):
    email = "pytest-super@example.com"
    secret = pyotp.random_base32()

    user = GlobalUserDB(
        email=email,
        password_hash=get_password_hash("TestPassword!123"),
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted=_encrypt_mfa_secret(secret),
        session_id=None,
        created_at=datetime.now(timezone.utc),
        created_by="pytest",
    )

    db.add(user)
    db.flush()

    return user, secret


def test_super_token_contains_global_identity(temporary_super):
    user, _secret = temporary_super
    user.session_id = "session-test-001"

    token = _create_super_token(user)

    from jose import jwt
    from UsersAPI.settings import settings

    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )

    assert payload["user_type"] == "SUPER"
    assert payload["global_user_id"] == user.id
    assert payload["session_id"] == "session-test-001"
    assert "tenant_id" not in payload
    assert "user_tenant_id" not in payload


def test_super_login_requires_mfa(temporary_super, db):
    user, _secret = temporary_super

    with pytest.raises(HTTPException) as exc_info:
        login_super_user(
            SuperLoginRequest(
                email=user.email,
                password="TestPassword!123",
            ),
            db,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Código MFA requerido"


def test_super_login_and_single_session(temporary_super, db):
    user, secret = temporary_super
    otp = pyotp.TOTP(secret).now()

    first = login_super_user(
        SuperLoginRequest(
            email=user.email,
            password="TestPassword!123",
            otp=otp,
        ),
        db,
    )

    first_session_id = first.session_id

    second_otp = pyotp.TOTP(secret).now()

    second = login_super_user(
        SuperLoginRequest(
            email=user.email,
            password="TestPassword!123",
            otp=second_otp,
        ),
        db,
    )

    assert first_session_id != second.session_id
    assert user.session_id == second.session_id

    with pytest.raises(HTTPException) as exc_info:
        get_current_super_user(
            first.access_token,
            db,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "La sesión SUPER ya no es válida"

    current = get_current_super_user(
        second.access_token,
        db,
    )

    assert current.id == user.id

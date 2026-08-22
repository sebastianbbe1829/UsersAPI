import pyotp
import pytest
from fastapi import HTTPException

from UsersAPI.models import GlobalUserDB
from UsersAPI.schemas.global_auth import SuperLoginRequest
from UsersAPI.services.global_auth_service import (
    _decrypt_mfa_secret,
    login_super_user,
)


def test_super_bootstrap_response_does_not_expose_mfa_secret():
    from UsersAPI.schemas.global_auth import SuperBootstrapResponse

    response = SuperBootstrapResponse(
        id=1,
        email="super@example.com",
        mfa_enabled=True,
        provisioning_uri="otpauth://totp/UsersAPI:super@example.com?secret=TEST&issuer=UsersAPI",
    )

    assert "mfa_secret" not in response.model_dump()


def test_multiple_super_users_are_valid_identities(db):
    users = [
        GlobalUserDB(
            email="super1@example.com",
            password_hash="hash",
            is_active=True,
            is_superuser=True,
            mfa_enabled=True,
            mfa_secret_encrypted="encrypted",
            created_at=__import__("datetime").datetime.utcnow(),
            created_by="test",
        ),
        GlobalUserDB(
            email="super2@example.com",
            password_hash="hash",
            is_active=True,
            is_superuser=True,
            mfa_enabled=True,
            mfa_secret_encrypted="encrypted",
            created_at=__import__("datetime").datetime.utcnow(),
            created_by="test",
        ),
    ]

    db.add_all(users)
    db.commit()

    assert (
        db.query(GlobalUserDB)
        .filter(GlobalUserDB.is_superuser.is_(True))
        .count()
        >= 2
    )


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

    first_session = first.session_id
    assert first.user_type == "SUPER"
    assert first_session

    db.refresh(user)
    assert user.session_id == first_session


def test_mfa_secret_is_stored_encrypted(temporary_super, db):
    user, secret = temporary_super

    assert user.mfa_secret_encrypted
    assert user.mfa_secret_encrypted != secret
    assert _decrypt_mfa_secret(user.mfa_secret_encrypted) == secret

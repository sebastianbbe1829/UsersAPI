from datetime import datetime, timezone

import pyotp
import pytest
from fastapi import HTTPException

from UsersAPI.database import BootstrapSessionLocal, set_rls_tenant
from UsersAPI.models import GlobalUserDB, TenantDB
from UsersAPI.schemas.global_auth import SuperLoginRequest
from UsersAPI.services.auth_service import get_password_hash
from UsersAPI.services.global_auth_service import (
    _create_super_token,
    _decrypt_mfa_secret,
    _encrypt_mfa_secret,
    get_current_super_user,
    login_super_user,
)


@pytest.fixture
def temporary_tenant(db_session):
    """Crea un tenant usando el contexto de bootstrap, que bypassa RLS."""
    bootstrap_db = BootstrapSessionLocal()

    tenant = TenantDB(
        name="Tenant SUPER Test",
        slug="tenant-super-test",
        status=1,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        created_by="pytest",
    )

    try:
        bootstrap_db.add(tenant)
        bootstrap_db.commit()
        bootstrap_db.refresh(tenant)

        # Las operaciones posteriores del test sobre la conexión normal
        # quedan sujetas a RLS para este tenant.
        set_rls_tenant(db_session, tenant.id)

        yield tenant

    finally:
        bootstrap_db.query(TenantDB).filter(TenantDB.id == tenant.id).delete()
        bootstrap_db.commit()
        bootstrap_db.close()


@pytest.fixture
def temporary_super(db_session, temporary_tenant):
    email = "pytest-super@example.com"
    secret = pyotp.random_base32()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    user = GlobalUserDB(
        email=email,
        password_hash=get_password_hash("TestPassword!123"),
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted=_encrypt_mfa_secret(secret),
        mfa_verified_at=now,
        session_id=None,
        created_at=now,
        created_by="pytest",
        updated_at=now,
        updated_by="pytest",
    )

    db_session.add(user)
    db_session.flush()

    return user, secret, temporary_tenant


def test_super_bootstrap_response_does_not_expose_mfa_secret():
    from UsersAPI.schemas.global_auth import SuperBootstrapResponse

    response = SuperBootstrapResponse(
        id=1,
        email="super@example.com",
        mfa_enabled=True,
        provisioning_uri=(
            "otpauth://totp/UsersAPI:super@example.com"
            "?secret=TEST&issuer=UsersAPI"
        ),
    )

    assert "mfa_secret" not in response.model_dump()


def test_multiple_super_users_are_valid_identities(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    users = [
        GlobalUserDB(
            email="super1@example.com",
            password_hash="hash",
            is_active=True,
            is_superuser=True,
            mfa_enabled=True,
            mfa_secret_encrypted="encrypted",
            created_at=now,
            created_by="pytest",
        ),
        GlobalUserDB(
            email="super2@example.com",
            password_hash="hash",
            is_active=True,
            is_superuser=True,
            mfa_enabled=True,
            mfa_secret_encrypted="encrypted",
            created_at=now,
            created_by="pytest",
        ),
    ]

    db_session.add_all(users)
    db_session.flush()

    count = (
        db_session.query(GlobalUserDB)
        .filter(GlobalUserDB.is_superuser.is_(True))
        .count()
    )

    assert count >= 2


def test_super_token_contains_global_and_tenant_identity(
    temporary_super,
):
    user, _secret, tenant = temporary_super

    user.session_id = "session-test-001"

    token = _create_super_token(user, tenant)

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
    assert payload["tenant_id"] == tenant.id
    assert payload["tenant_slug"] == tenant.slug


def test_super_login_requires_mfa(db_session, temporary_tenant):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    secret = pyotp.random_base32()

    user = GlobalUserDB(
        email="super-mfa-required@example.com",
        password_hash=get_password_hash("TestPassword!123"),
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted=_encrypt_mfa_secret(secret),
        mfa_verified_at=None,
        session_id=None,
        created_at=now,
        created_by="pytest",
        updated_at=now,
        updated_by="pytest",
    )

    db_session.add(user)
    db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        login_super_user(
            SuperLoginRequest(
                email=user.email,
                password="TestPassword!123",
                tenant=temporary_tenant.slug,
            ),
            db_session,
        )

    assert exc_info.value.status_code == 403
    assert (
        exc_info.value.detail
        == "El MFA del usuario SUPER aún no ha sido verificado"
    )


def test_super_login_and_single_session(
    temporary_super,
    db_session,
):
    user, secret, tenant = temporary_super

    first_otp = pyotp.TOTP(secret).now()

    first = login_super_user(
        SuperLoginRequest(
            email=user.email,
            password="TestPassword!123",
            otp=first_otp,
            tenant=tenant.slug,
        ),
        db_session,
    )

    first_session_id = first.session_id

    assert first.user_type == "SUPER"
    assert first_session_id
    assert first.tenant_id == tenant.id
    assert first.tenant_slug == tenant.slug

    db_session.refresh(user)

    assert user.session_id == first_session_id

    second_otp = pyotp.TOTP(secret).now()

    second = login_super_user(
        SuperLoginRequest(
            email=user.email,
            password="TestPassword!123",
            otp=second_otp,
            tenant=tenant.slug,
        ),
        db_session,
    )

    assert first_session_id != second.session_id
    assert user.session_id == second.session_id

    with pytest.raises(HTTPException) as exc_info:
        get_current_super_user(
            first.access_token,
            db_session,
        )

    assert exc_info.value.status_code == 401
    assert (
        exc_info.value.detail
        == "La sesión SUPER ya no es válida"
    )

    current = get_current_super_user(
        second.access_token,
        db_session,
    )

    assert current.id == user.id


def test_mfa_secret_is_stored_encrypted(temporary_super):
    user, secret, _tenant = temporary_super

    assert user.mfa_secret_encrypted
    assert user.mfa_secret_encrypted != secret
    assert _decrypt_mfa_secret(
        user.mfa_secret_encrypted
    ) == secret

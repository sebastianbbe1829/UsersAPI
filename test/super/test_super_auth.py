from datetime import datetime, timezone

import pyotp
import pytest
from fastapi import HTTPException

from UsersAPI.database import BootstrapSessionLocal, set_rls_tenant
from UsersAPI.models import GlobalUserDB, TenantDB
from UsersAPI.services.password_service import get_password_hash
from UsersAPI.schemas.global_auth import SuperLoginRequest
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
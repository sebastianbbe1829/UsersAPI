from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.controllers.auth_controller import create_access_token
from UsersAPI.models import AuthAuditDB, TenantConfigDB
from test.fixtures.multitenant import create_user_context


def _set_max_login_attempts(db_session: Session, tenant_id: int, value: int):
    config = TenantConfigDB(
        tenant_id=tenant_id,
        app_title="Test",
        logo_url=None,
        primary_color="#0D6EFD",
        secondary_color="#6C757D",
        max_login_attempts=value,
        created_at=datetime.now(),
        created_by="test",
    )
    db_session.add(config)
    db_session.flush()
    return config


def test_login_accepts_user_with_authenticate_permission(db_session: Session, client: TestClient):
    _, tenant, user_tenant, _ = create_user_context(db_session, password="segura123")

    response = client.post(
        "/auth/login",
        json={"username": user_tenant.email, "password": "segura123", "tenant": tenant.slug},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]

    audit = (
        db_session.query(AuthAuditDB)
        .filter(AuthAuditDB.user_tenant_id == user_tenant.id, AuthAuditDB.event_type == "LOGIN_SUCCESS")
        .order_by(AuthAuditDB.occurred_at.desc())
        .first()
    )
    assert audit is not None
    assert audit.actor_dni == user_tenant.user.dni
    assert audit.actor_login == user_tenant.email


def test_login_rejects_wrong_tenant(db_session: Session, client: TestClient):
    _, _, user_tenant, _ = create_user_context(db_session, password="segura123")

    response = client.post(
        "/auth/login",
        json={"username": user_tenant.email, "password": "segura123", "tenant": "tenant-that-does-not-exist"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Tenant inválido"


def test_expired_token_is_rejected_by_validate_endpoint(db_session: Session, client: TestClient):
    user, tenant, user_tenant, _ = create_user_context(db_session)

    token = create_access_token(
        {"sub": user.dni, "tenant_id": tenant.id, "tenant_slug": tenant.slug, "user_tenant_id": user_tenant.id},
        expires_delta=timedelta(minutes=-5),
    )

    response = client.get("/auth/validate", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_login_locks_after_tenant_configured_attempts_and_audits_lock(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    _, tenant, user_tenant, _ = create_user_context(db_session, password="segura123")
    _set_max_login_attempts(db_session, tenant.id, 2)
    monkeypatch.setattr(
        "UsersAPI.services.auth_service.notify_tenant_admins_account_locked",
        lambda *args, **kwargs: None,
    )

    for _ in range(2):
        response = client.post(
            "/auth/login",
            json={"username": user_tenant.email, "password": "incorrecta", "tenant": tenant.slug},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cuenta bloqueada, comuníquese con el administrador"

    db_session.refresh(user_tenant)
    assert user_tenant.failed_login_attempts == 2
    assert user_tenant.locked_at is not None
    assert user_tenant.locked_ip

    events = (
        db_session.query(AuthAuditDB)
        .filter(AuthAuditDB.user_tenant_id == user_tenant.id)
        .order_by(AuthAuditDB.occurred_at.asc())
        .all()
    )
    assert [event.event_type for event in events if event.event_type in {"LOGIN_FAILED", "ACCOUNT_LOCKED"}] == [
        "LOGIN_FAILED",
        "LOGIN_FAILED",
        "ACCOUNT_LOCKED",
    ]
    assert all(event.actor_login == user_tenant.email for event in events if event.event_type in {"LOGIN_FAILED", "ACCOUNT_LOCKED"})
    assert all(event.actor_dni == user_tenant.user.dni for event in events if event.event_type in {"LOGIN_FAILED", "ACCOUNT_LOCKED"})

    correct_password = client.post(
        "/auth/login",
        json={"username": user_tenant.email, "password": "segura123", "tenant": tenant.slug},
    )
    assert correct_password.status_code == 403
    assert correct_password.json()["detail"] == "Cuenta bloqueada, comuníquese con el administrador"


def test_zero_login_attempt_limit_does_not_lock_account(db_session: Session, client: TestClient):
    _, tenant, user_tenant, _ = create_user_context(db_session, password="segura123")
    _set_max_login_attempts(db_session, tenant.id, 0)

    for _ in range(4):
        response = client.post(
            "/auth/login",
            json={"username": user_tenant.email, "password": "incorrecta", "tenant": tenant.slug},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Credenciales inválidas"

    db_session.refresh(user_tenant)
    assert user_tenant.failed_login_attempts == 4
    assert user_tenant.locked_at is None

    success = client.post(
        "/auth/login",
        json={"username": user_tenant.email, "password": "segura123", "tenant": tenant.slug},
    )
    assert success.status_code == 200
    db_session.refresh(user_tenant)
    assert user_tenant.failed_login_attempts == 0
    assert user_tenant.locked_at is None

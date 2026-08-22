from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.controllers.auth_controller import create_access_token
from test.fixtures.multitenant import create_user_context


def test_login_accepts_user_with_authenticate_permission(
    db_session: Session,
    client: TestClient,
):
    _, tenant, user_tenant, _ = create_user_context(
        db_session,
        password="segura123",
    )

    response = client.post(
        "/auth/login",
        json={
            "username": user_tenant.email,
            "password": "segura123",
            "tenant": tenant.slug,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_rejects_wrong_tenant(
    db_session: Session,
    client: TestClient,
):
    _, _, user_tenant, _ = create_user_context(
        db_session,
        password="segura123",
    )

    response = client.post(
        "/auth/login",
        json={
            "username": user_tenant.email,
            "password": "segura123",
            "tenant": "tenant-that-does-not-exist",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Credenciales inválidas o usuario inactivo"
    )


def test_expired_token_is_rejected_by_validate_endpoint(
    db_session: Session,
    client: TestClient,
):
    user, tenant, user_tenant, _ = create_user_context(db_session)

    token = create_access_token(
        {
            "sub": user.dni,
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_tenant_id": user_tenant.id,
        },
        expires_delta=timedelta(minutes=-5),
    )

    response = client.get(
        "/auth/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

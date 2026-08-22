from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.controllers.auth_controller import (
    create_access_token,
    pwd_context,
    verify_password,
)
from test.fixtures.multitenant import create_user_context


def test_password_verification_in_memory():
    plain = "123456"
    hash_value = pwd_context.hash(plain)

    assert verify_password(plain, hash_value) is True
    assert verify_password("otrovalor", hash_value) is False


def test_password_update_is_stored_once_and_can_be_verified(
    db_session: Session,
    client: TestClient,
):
    user, tenant, user_tenant, token = create_user_context(db_session)

    response = client.patch(
        f"/users/{user.dni}",
        json={"password": "newpass"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    db_session.expire_all()
    db_session.refresh(user_tenant)
    assert verify_password("newpass", user_tenant.password) is True
    assert verify_password("oldpass", user_tenant.password) is False


def test_invalid_user_payload_returns_validation_error(
    db_session: Session,
    client: TestClient,
):
    user, _, _, token = create_user_context(db_session)

    response = client.post(
        "/users",
        json={"dni": user.dni, "name": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_expired_token_returns_expired_message(
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
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expirado"

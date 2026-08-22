from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.database import SessionLocal
from UsersAPI.main import app
from UsersAPI.models import UserDB, UserTenantDB
from test.fixtures.multitenant import create_user_context


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


def test_create_user_returns_201_and_persists_user(
    db_session: Session,
    client: TestClient,
):
    creator, tenant, user_tenant, token = create_user_context(
        db_session,
        password="segura123",
        name="Creator",
    )

    new_dni = f"{uuid4().int % 100000000:08d}"
    new_email = f"{uuid4().hex[:8]}@example.com"

    response = client.post(
        "/users",
        json={
            "dni": new_dni,
            "name": "Nuevo Usuario",
            "email": new_email,
            "phone": "3000000000",
            "password": "segura123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["dni"] == new_dni
    assert payload["email"] == new_email
    assert payload["status"] == 0
    assert "password" not in payload
    assert "activation_token" not in payload

    stored = (
        db_session.query(UserDB)
        .filter(UserDB.dni == new_dni)
        .first()
    )
    assert stored is not None

    link = (
        db_session.query(UserTenantDB)
        .filter(
            UserTenantDB.user_id == stored.id,
            UserTenantDB.tenant_id == tenant.id,
        )
        .first()
    )
    assert link is not None
    assert link.email == new_email
    assert link.status == 0


def test_same_user_can_exist_in_multiple_tenants(
    db_session: Session,
    client: TestClient,
):
    user_a, tenant_a, _, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )
    _, tenant_b, _, _ = create_user_context(
        db_session,
        password="segura123",
        name="Admin B",
    )

    email_b = f"{uuid4().hex[:8]}@example.com"

    response = client.post(
        "/user-tenants",
        json={
            "user_id": user_a.id,
            "tenant_id": tenant_b.id,
            "email": email_b,
            "password": "segura123",
            "phone": "3000000000",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # El usuario del tenant A no puede crear directamente una asociación
    # apuntando al tenant B. La creación debe estar siempre limitada al
    # tenant del contexto autenticado.
    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    links = (
        db_session.query(UserTenantDB)
        .filter(UserTenantDB.user_id == user_a.id)
        .all()
    )
    assert len(links) == 1
    assert links[0].tenant_id == tenant_a.id


def test_delete_user_is_logical_and_scoped_to_current_tenant(
    db_session: Session,
    client: TestClient,
):
    user, tenant, user_tenant, token = create_user_context(
        db_session,
        password="segura123",
        name="Usuario Borrar",
    )

    response = client.delete(
        f"/users/{user.dni}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Usuario eliminado correctamente"
    assert payload["dni"] == user.dni
    assert payload["email"] == user_tenant.email
    assert payload["name"] == "Usuario Borrar"
    assert payload["phone"] == "3000000000"
    assert payload["id"] == user.id
    assert "password" not in payload
    assert "activation_token" not in payload

    db_session.expire_all()
    deleted_link = (
        db_session.query(UserTenantDB)
        .filter(
            UserTenantDB.user_id == user.id,
            UserTenantDB.tenant_id == tenant.id,
        )
        .first()
    )

    assert deleted_link is not None
    assert deleted_link.status == 3


def test_get_user_list_requires_authentication(client: TestClient):
    response = client.get("/users")
    assert response.status_code == 401


def test_legacy_users_bootstrap_endpoint_is_not_registered(
    client: TestClient,
):
    response = client.post(
        "/users/bootstrap",
        json={
            "dni": "99999999",
            "name": "Legacy Bootstrap",
            "email": "legacy@example.com",
            "phone": "3000000000",
            "password": "segura123",
        },
    )

    assert response.status_code == 404

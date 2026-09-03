from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.database import BootstrapSessionLocal
from UsersAPI.models import UserDB, UserTenantDB
from UsersAPI.settings import settings
from test.fixtures.multitenant import create_user_context


def test_create_user_returns_201_and_persists_user(db_session: Session, client: TestClient):
    _, tenant, _, token = create_user_context(
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

    stored = db_session.query(UserDB).filter(UserDB.dni == new_dni).first()
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


def test_legacy_users_bootstrap_endpoint_is_not_registered(client: TestClient):
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
    # /users/bootstrap ya no existe como endpoint POST. FastAPI
    # resuelve "bootstrap" como el parámetro {dni} de GET/PATCH/DELETE,
    # por lo que un POST recibe 405 Method Not Allowed.
    assert response.status_code == 405


def _bootstrap_payload(suffix: str) -> dict:
    return {
        "tenant_name": f"Empresa Bootstrap {suffix}",
        "tenant_slug": f"empresa-bootstrap-{suffix}",
        "admin_dni": f"{uuid4().int % 100000000:08d}",
        "admin_name": "Administrador Inicial",
        "admin_email": f"admin-{suffix}@example.com",
        "admin_password": "segura123",
        "admin_phone": "3000000000",
    }


def _bootstrap_headers() -> dict:
    return {"X-Bootstrap-Tenant-Key": settings.bootstrap_tenant_key}


def test_bootstrap_creates_tenant_and_admin(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    from UsersAPI.services import bootstrap_tenant_service

    monkeypatch.setattr(bootstrap_tenant_service, "send_email", lambda **kwargs: None)
    monkeypatch.setattr(bootstrap_tenant_service, "send_whatsapp", lambda **kwargs: None)

    suffix = uuid4().hex[:10]
    payload = _bootstrap_payload(suffix)

    response = client.post(
        "/bootstrap",
        json=payload,
        headers=_bootstrap_headers(),
    )

    assert response.status_code == 201
    result = response.json()
    assert result["tenant_name"] == payload["tenant_name"]
    assert result["tenant_slug"] == payload["tenant_slug"]
    assert result["user_dni"] == payload["admin_dni"]
    assert result["user_name"] == payload["admin_name"]
    assert result["user_email"] == payload["admin_email"]
    assert result["role_code"] == "ADMIN"
    assert result["role_name"] == "Administrador"

    # /bootstrap confirma usando users_api_bootstrap (BYPASSRLS), por lo que
    # la persistencia debe verificarse con esa misma conexión y no con la
    # sesión de aplicación, cuyo contexto RLS no pertenece al tenant creado.
    verification_db = BootstrapSessionLocal()
    try:
        user_tenant = verification_db.get(UserTenantDB, result["user_tenant_id"])
        assert user_tenant is not None
        assert user_tenant.tenant_id == result["tenant_id"]
        assert user_tenant.status == 0
    finally:
        verification_db.close()


def test_bootstrap_can_provision_multiple_tenants(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    """Bootstrap se ejecuta por empresa; no es una inicialización global única."""
    from UsersAPI.services import bootstrap_tenant_service

    monkeypatch.setattr(bootstrap_tenant_service, "send_email", lambda **kwargs: None)
    monkeypatch.setattr(bootstrap_tenant_service, "send_whatsapp", lambda **kwargs: None)

    first_suffix = uuid4().hex[:10]
    second_suffix = uuid4().hex[:10]

    first = client.post(
        "/bootstrap",
        json=_bootstrap_payload(first_suffix),
        headers=_bootstrap_headers(),
    )
    second = client.post(
        "/bootstrap",
        json=_bootstrap_payload(second_suffix),
        headers=_bootstrap_headers(),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["tenant_slug"] != second.json()["tenant_slug"]
    assert first.json()["tenant_id"] != second.json()["tenant_id"]


def test_bootstrap_rejects_duplicate_tenant_slug(
    db_session: Session,
    client: TestClient,
    monkeypatch,
):
    from UsersAPI.services import bootstrap_tenant_service

    monkeypatch.setattr(bootstrap_tenant_service, "send_email", lambda **kwargs: None)
    monkeypatch.setattr(bootstrap_tenant_service, "send_whatsapp", lambda **kwargs: None)

    suffix = uuid4().hex[:10]
    payload = _bootstrap_payload(suffix)

    first = client.post("/bootstrap", json=payload, headers=_bootstrap_headers())
    assert first.status_code == 201

    second = client.post(
        "/bootstrap",
        json={
            **payload,
            "admin_dni": f"{uuid4().int % 100000000:08d}",
            "admin_email": f"other-{suffix}@example.com",
        },
        headers=_bootstrap_headers(),
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "El tenant ya existe."

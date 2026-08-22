from uuid import uuid4

import pytest

from UsersAPI.models import (
    PermissionDB,
    RoleDB,
    RolePermissionDB,
    TenantDB,
    UserDB,
    UserTenantDB,
    UserTenantRoleDB,
)
from UsersAPI.security.permission_definitions import PERMISSIONS
from UsersAPI.services import bootstrap_service


BOOTSTRAP_KEY = "test-bootstrap-key"


@pytest.fixture(autouse=True)
def configure_bootstrap(monkeypatch):
    """Configura la clave interna y desactiva servicios externos en tests."""
    monkeypatch.setenv("BOOTSTRAP_KEY", BOOTSTRAP_KEY)
    monkeypatch.setattr(bootstrap_service, "send_email", lambda **kwargs: None)
    monkeypatch.setattr(bootstrap_service, "send_whatsapp", lambda **kwargs: None)


def _bootstrap_headers(key: str = BOOTSTRAP_KEY):
    return {"X-Bootstrap-Key": key}


def _bootstrap_payload(suffix: str, *, dni: str | None = None):
    return {
        "tenant_name": f"Empresa {suffix}",
        "tenant_slug": f"empresa-{suffix}",
        "admin_dni": dni or f"{uuid4().int % 100000000:08d}",
        "admin_name": f"Administrador {suffix}",
        "admin_email": f"admin-{suffix}@example.com",
        "admin_password": "segura123",
        "admin_phone": "3000000000",
    }


def test_bootstrap_requires_internal_key(client):
    payload = _bootstrap_payload("sin-clave")

    response = client.post("/bootstrap", json=payload)

    assert response.status_code == 422


def test_bootstrap_rejects_invalid_internal_key(client):
    payload = _bootstrap_payload("clave-invalida")

    response = client.post(
        "/bootstrap",
        json=payload,
        headers=_bootstrap_headers("clave-incorrecta"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Clave de bootstrap inválida."


def test_bootstrap_creates_new_tenant_with_admin_context(db_session, client):
    payload = _bootstrap_payload("uno")

    response = client.post(
        "/bootstrap",
        json=payload,
        headers=_bootstrap_headers(),
    )

    assert response.status_code == 201
    body = response.json()

    assert body["tenant_name"] == payload["tenant_name"]
    assert body["tenant_slug"] == payload["tenant_slug"]
    assert body["user_dni"] == payload["admin_dni"]
    assert body["user_email"] == payload["admin_email"]
    assert body["role_code"] == "ADMIN"

    tenant = db_session.query(TenantDB).filter(
        TenantDB.slug == payload["tenant_slug"]
    ).one()
    user = db_session.query(UserDB).filter(
        UserDB.dni == payload["admin_dni"]
    ).one()
    user_tenant = db_session.query(UserTenantDB).filter(
        UserTenantDB.tenant_id == tenant.id,
        UserTenantDB.user_id == user.id,
    ).one()

    admin_role = db_session.query(RoleDB).filter(
        RoleDB.tenant_id == tenant.id,
        RoleDB.code == "ADMIN",
    ).one()
    authenticate_role = db_session.query(RoleDB).filter(
        RoleDB.tenant_id == tenant.id,
        RoleDB.code == "AUTHENTICATE",
    ).one()

    assert user_tenant.email == payload["admin_email"]
    assert user_tenant.status == 0

    assigned_role = db_session.query(UserTenantRoleDB).filter(
        UserTenantRoleDB.user_tenant_id == user_tenant.id,
        UserTenantRoleDB.role_id == admin_role.id,
    ).one_or_none()
    assert assigned_role is not None

    admin_permission_count = db_session.query(RolePermissionDB).filter(
        RolePermissionDB.role_id == admin_role.id
    ).count()
    assert admin_permission_count == len(PERMISSIONS)

    auth_permission = db_session.query(RolePermissionDB).filter(
        RolePermissionDB.role_id == authenticate_role.id,
        RolePermissionDB.permission_id == db_session.query(PermissionDB.id)
        .filter(PermissionDB.code == "AUTHENTICATE")
        .scalar_subquery(),
    ).one_or_none()
    assert auth_permission is not None


def test_bootstrap_allows_a_second_company(db_session, client):
    first = _bootstrap_payload("uno")
    second = _bootstrap_payload("dos")

    first_response = client.post(
        "/bootstrap",
        json=first,
        headers=_bootstrap_headers(),
    )
    second_response = client.post(
        "/bootstrap",
        json=second,
        headers=_bootstrap_headers(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    tenants = db_session.query(TenantDB).filter(
        TenantDB.slug.in_([first["tenant_slug"], second["tenant_slug"]])
    ).all()
    assert {tenant.slug for tenant in tenants} == {
        first["tenant_slug"],
        second["tenant_slug"],
    }

    first_user = db_session.query(UserDB).filter(
        UserDB.dni == first["admin_dni"]
    ).one()
    second_user = db_session.query(UserDB).filter(
        UserDB.dni == second["admin_dni"]
    ).one()

    assert first_user.id != second_user.id


def test_bootstrap_can_reuse_global_user_for_another_tenant(db_session, client):
    admin_dni = f"{uuid4().int % 100000000:08d}"
    first = _bootstrap_payload("uno", dni=admin_dni)
    second = _bootstrap_payload("dos", dni=admin_dni)

    assert client.post(
        "/bootstrap",
        json=first,
        headers=_bootstrap_headers(),
    ).status_code == 201
    second_response = client.post(
        "/bootstrap",
        json=second,
        headers=_bootstrap_headers(),
    )

    assert second_response.status_code == 201

    user = db_session.query(UserDB).filter(UserDB.dni == admin_dni).one()
    links = db_session.query(UserTenantDB).filter(
        UserTenantDB.user_id == user.id
    ).all()

    assert len(links) == 2
    assert {link.email for link in links} == {
        first["admin_email"],
        second["admin_email"],
    }


def test_bootstrap_rejects_duplicate_tenant_slug(client):
    payload = _bootstrap_payload("unico")

    first_response = client.post(
        "/bootstrap",
        json=payload,
        headers=_bootstrap_headers(),
    )
    second_response = client.post(
        "/bootstrap",
        json=payload,
        headers=_bootstrap_headers(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "El tenant ya existe."

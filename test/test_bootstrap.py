from uuid import uuid4

import importlib
import pytest
from sqlalchemy import text

from UsersAPI.models import (
    PermissionDB,
    RoleDB,
    RolePermissionDB,
    TenantDB,
    TenantConfigDB,
    UserDB,
    UserTenantDB,
    UserTenantRoleDB,
)
from UsersAPI.security.permission_definitions import PERMISSIONS
from UsersAPI.services import bootstrap_tenant_service
from UsersAPI.settings import Settings


BOOTSTRAP_TENANT_KEY = "test-bootstrap-tenant-key"


@pytest.fixture(autouse=True)
def configure_bootstrap(monkeypatch):
    """Configura la clave interna y desactiva servicios externos en tests."""
    monkeypatch.setenv("BOOTSTRAP_TENANT_KEY", BOOTSTRAP_TENANT_KEY)

    # El paquete UsersAPI.routes expone bootstrap_tenant_routes como APIRouter.
    # Para reemplazar la referencia `settings` usada por la ruta debemos
    # obtener el módulo real que contiene bootstrap_route.
    bootstrap_routes_module = importlib.import_module(
        "UsersAPI.routes.bootstrap_tenant_routes"
    )

    monkeypatch.setattr(
        bootstrap_routes_module,
        "settings",
        Settings(bootstrap_tenant_key=BOOTSTRAP_TENANT_KEY),
    )

    monkeypatch.setattr(bootstrap_tenant_service, "send_email", lambda **kwargs: None)
    monkeypatch.setattr(bootstrap_tenant_service, "send_whatsapp", lambda **kwargs: None)


def _bootstrap_headers(key: str = BOOTSTRAP_TENANT_KEY):
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

    # Las consultas posteriores deben ejecutarse con el mismo tenant context
    # utilizado por RLS en la aplicación. El nombre correcto de la variable
    # de sesión es app.current_tenant_id.
    db_session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(body["tenant_id"])},
    )

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

    config = db_session.query(TenantConfigDB).filter(
        TenantConfigDB.tenant_id == tenant.id
    ).one()

    assert config.app_title == payload["tenant_name"]
    assert config.logo_url is None
    assert config.primary_color == "#0D6EFD"
    assert config.secondary_color == "#6C757D"
    assert config.created_by == payload["admin_dni"]

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

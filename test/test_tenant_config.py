from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.database import set_rls_tenant
from UsersAPI.models import TenantConfigDB
from test.fixtures.multitenant import create_user_context
from test.test_multitenant_isolation import grant_permissions


def test_tenant_config_is_created_with_defaults(
    db_session: Session,
    client: TestClient,
):
    _, tenant, user_tenant, token = create_user_context(
        db_session,
        password="segura123",
        name="Admin Config",
    )

    tenant_id = tenant.id
    grant_permissions(db_session, user_tenant, "TENANT_READ")

    response = client.get(
        "/tenant-config",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == tenant_id
    assert data["name"] == tenant.name
    assert data["slug"] == tenant.slug
    assert data["app_title"] == tenant.name
    assert data["logo_url"] is None
    assert data["primary_color"] == "#0D6EFD"
    assert data["secondary_color"] == "#6C757D"

    config = (
        db_session.query(TenantConfigDB)
        .filter(TenantConfigDB.tenant_id == tenant_id)
        .one()
    )
    assert config.app_title == tenant.name


def test_tenant_can_update_own_ui_config(
    db_session: Session,
    client: TestClient,
):
    _, tenant, user_tenant, token = create_user_context(
        db_session,
        password="segura123",
        name="Admin Config",
    )

    grant_permissions(db_session, user_tenant, "TENANT_READ", "TENANT_UPDATE")

    response = client.patch(
        "/tenant-config",
        json={
            "app_title": "Mi Aplicación",
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#112233",
            "secondary_color": "#AABBCC",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == tenant.id
    assert data["app_title"] == "Mi Aplicación"
    assert data["logo_url"] == "https://example.com/logo.png"
    assert data["primary_color"] == "#112233"
    assert data["secondary_color"] == "#AABBCC"


def test_tenant_config_update_isolated_from_another_tenant(
    db_session: Session,
    client: TestClient,
):
    _, tenant_a, user_tenant_a, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )
    _, tenant_b, _, _ = create_user_context(
        db_session,
        password="segura123",
        name="Admin B",
    )

    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id

    # Creamos explícitamente la configuración de B bajo su propio contexto.
    set_rls_tenant(db_session, tenant_b_id)
    db_session.add(
        TenantConfigDB(
            tenant_id=tenant_b_id,
            app_title="Configuración B",
            logo_url=None,
            primary_color="#445566",
            secondary_color="#778899",
            created_at=datetime.now(),
            created_by="test",
        )
    )
    db_session.flush()

    grant_permissions(db_session, user_tenant_a, "TENANT_READ", "TENANT_UPDATE")

    response = client.patch(
        "/tenant-config",
        json={"app_title": "Configuración A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_a_id

    set_rls_tenant(db_session, tenant_b_id)
    config_b = (
        db_session.query(TenantConfigDB)
        .filter(TenantConfigDB.tenant_id == tenant_b_id)
        .one()
    )

    assert config_b.app_title == "Configuración B"
    assert config_b.primary_color == "#445566"


def test_tenant_config_requires_permission(
    db_session: Session,
    client: TestClient,
):
    _, _, user_tenant, token = create_user_context(
        db_session,
        password="segura123",
        name="Admin Sin Permiso",
    )

    grant_permissions(db_session, user_tenant, "TENANT_READ")

    response = client.patch(
        "/tenant-config",
        json={"app_title": "No permitido"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "No tienes permisos para realizar esta operación"
    )


def test_tenant_config_rejects_invalid_colors(
    db_session: Session,
    client: TestClient,
):
    _, _, user_tenant, token = create_user_context(
        db_session,
        password="segura123",
        name="Admin Config",
    )

    grant_permissions(db_session, user_tenant, "TENANT_UPDATE")

    response = client.patch(
        "/tenant-config",
        json={"primary_color": "red"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422

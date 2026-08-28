from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.models import PermissionDB, RolePermissionDB
from test.fixtures.multitenant import create_user_context


def grant_permissions(db: Session, user_tenant, *permission_codes: str):
    """Concede permisos al rol del contexto de prueba."""
    role_id = user_tenant.roles[0].role_id

    for code in permission_codes:
        permission = (
            db.query(PermissionDB)
            .filter(PermissionDB.code == code)
            .first()
        )

        if permission is None:
            raise AssertionError(
                f"El permiso requerido por la prueba no existe: {code}"
            )

        exists = (
            db.query(RolePermissionDB)
            .filter(
                RolePermissionDB.role_id == role_id,
                RolePermissionDB.permission_id == permission.id,
            )
            .first()
        )

        if exists is None:
            db.add(
                RolePermissionDB(
                    role_id=role_id,
                    permission_id=permission.id,
                )
            )

    db.flush()
    db.expire_all()


def test_tenant_cannot_read_another_tenant(
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

    grant_permissions(db_session, user_tenant_a, "TENANT_READ")

    response = client.get(
        f"/tenants/{tenant_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    own_response = client.get(
        f"/tenants/{tenant_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert own_response.status_code == 200
    assert own_response.json()["id"] == tenant_a.id


def test_tenant_cannot_update_another_tenant(
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

    grant_permissions(db_session, user_tenant_a, "TENANT_UPDATE")
    original_name = tenant_b.name

    response = client.patch(
        f"/tenants/{tenant_b.id}",
        json={"name": "Tenant comprometido"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    db_session.expire_all()
    assert db_session.get(type(tenant_b), tenant_b.id).name == original_name
    assert tenant_a.id != tenant_b.id


def test_tenant_cannot_delete_another_tenant(
    db_session: Session,
    client: TestClient,
):
    _, _, user_tenant_a, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )
    _, tenant_b, _, _ = create_user_context(
        db_session,
        password="segura123",
        name="Admin B",
    )

    grant_permissions(db_session, user_tenant_a, "TENANT_DELETE")

    response = client.delete(
        f"/tenants/{tenant_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    db_session.expire_all()
    assert db_session.get(type(tenant_b), tenant_b.id).status == 1


def test_user_tenant_cannot_list_another_tenant(
    db_session: Session,
    client: TestClient,
):
    _, _, user_tenant_a, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )
    _, tenant_b, _, _ = create_user_context(
        db_session,
        password="segura123",
        name="Admin B",
    )

    grant_permissions(db_session, user_tenant_a, "USER_READ")

    response = client.get(
        f"/user-tenants/tenant/{tenant_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"


def test_user_tenant_cannot_create_association_in_another_tenant(
    db_session: Session,
    client: TestClient,
):
    user_a, _, user_tenant_a, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )
    _, tenant_b, _, _ = create_user_context(
        db_session,
        password="segura123",
        name="Admin B",
    )

    grant_permissions(db_session, user_tenant_a, "USER_UPDATE")
    email = f"{uuid4().hex[:8]}@example.com"

    response = client.post(
        "/user-tenants",
        json={
            "user_id": user_a.id,
            "tenant_id": tenant_b.id,
            "email": email,
            "password": "segura123",
            "phone": "3000000000",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"


def test_user_tenant_cannot_read_or_delete_association_from_another_tenant(
    db_session: Session,
    client: TestClient,
):
    _, _, user_tenant_a, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )
    _, _, user_tenant_b, _ = create_user_context(
        db_session,
        password="segura123",
        name="Admin B",
    )

    grant_permissions(
        db_session,
        user_tenant_a,
        "USER_READ",
        "USER_UPDATE",
    )

    read_response = client.get(
        f"/user-tenants/{user_tenant_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert read_response.status_code == 404
    assert read_response.json()["detail"] == (
        "Asociación usuario-tenant no encontrada"
    )

    delete_response = client.delete(
        f"/user-tenants/{user_tenant_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == (
        "Asociación usuario-tenant no encontrada"
    )

    db_session.expire_all()
    assert db_session.get(type(user_tenant_b), user_tenant_b.id).status == 1

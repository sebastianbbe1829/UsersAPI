from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.database import BootstrapSessionLocal, set_rls_tenant
from UsersAPI.models import PermissionDB, RoleDB, RolePermissionDB
from test.fixtures.multitenant import create_user_context
from test.test_multitenant_isolation import grant_permissions


def get_permission_id(db: Session, code: str) -> int:
    permission = db.query(PermissionDB).filter(PermissionDB.code == code).first()
    if permission is None:
        raise AssertionError(f"El permiso requerido por la prueba no existe: {code}")
    return permission.id


def test_role_crud_requires_permission(
    db_session: Session,
    client: TestClient,
):
    _, tenant_a, user_tenant_a, token_a = create_user_context(
        db_session,
        password="segura123",
        name="Admin A",
    )

    response = client.post(
        "/roles",
        json={
            "code": "REPORT_VIEWER",
            "name": "Consultor de reportes",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 403

    grant_permissions(db_session, user_tenant_a, "ROLE_CREATE")

    response = client.post(
        "/roles",
        json={
            "code": "REPORT_VIEWER",
            "name": "Consultor de reportes",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 201
    assert response.json()["tenant_id"] == tenant_a.id
    assert response.json()["code"] == "REPORT_VIEWER"


def test_roles_are_isolated_between_tenants(
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

    grant_permissions(
        db_session,
        user_tenant_a,
        "ROLE_CREATE",
        "ROLE_READ",
        "ROLE_UPDATE",
        "ROLE_DELETE",
    )

    set_rls_tenant(db_session, tenant_b_id)
    role_b = RoleDB(
        tenant_id=tenant_b_id,
        code=f"B-{uuid4().hex[:8]}",
        name="Rol privado B",
        status=1,
        created_by="test",
    )
    db_session.add(role_b)
    db_session.flush()
    role_b_id = role_b.id
    role_b_code = role_b.code

    set_rls_tenant(db_session, tenant_a_id)

    list_response = client.get(
        "/roles",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert list_response.status_code == 200
    assert all(role["tenant_id"] == tenant_a_id for role in list_response.json())
    assert all(role["code"] != role_b_code for role in list_response.json())

    get_response = client.get(
        f"/roles/{role_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Rol no encontrado"

    update_response = client.patch(
        f"/roles/{role_b_id}",
        json={"name": "Rol comprometido"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Rol no encontrado"

    delete_response = client.delete(
        f"/roles/{role_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Rol no encontrado"

    verification_db = BootstrapSessionLocal()
    try:
        role_b_after = verification_db.get(RoleDB, role_b_id)
        assert role_b_after is not None
        assert role_b_after.name == "Rol privado B"
        assert role_b_after.tenant_id == tenant_b_id
    finally:
        verification_db.close()


def test_role_permissions_are_isolated_between_tenants(
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
    grant_permissions(db_session, user_tenant_a, "ROLE_READ", "ROLE_UPDATE")

    permission_id = get_permission_id(db_session, "USER_READ")

    set_rls_tenant(db_session, tenant_b_id)
    role_b = RoleDB(
        tenant_id=tenant_b_id,
        code=f"B-{uuid4().hex[:8]}",
        name="Rol B",
        status=1,
        created_by="test",
    )
    db_session.add(role_b)
    db_session.flush()

    relation_b = RolePermissionDB(
        role_id=role_b.id,
        permission_id=permission_id,
    )
    db_session.add(relation_b)
    db_session.flush()
    role_b_id = role_b.id
    relation_b_id = relation_b.id

    set_rls_tenant(db_session, tenant_a_id)

    list_response = client.get(
        f"/role-permissions/role/{role_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert list_response.status_code == 404
    assert list_response.json()["detail"] == "El rol no existe en el tenant seleccionado"

    delete_response = client.delete(
        f"/role-permissions/{relation_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert delete_response.status_code == 404

    verification_db = BootstrapSessionLocal()
    try:
        relation_after = verification_db.get(RolePermissionDB, relation_b_id)
        assert relation_after is not None
        assert relation_after.role_id == role_b_id
        assert relation_after.permission_id == permission_id
    finally:
        verification_db.close()

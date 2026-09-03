from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from UsersAPI.database import BootstrapSessionLocal, set_rls_tenant
from UsersAPI.models import PermissionDB, RolePermissionDB
from test.fixtures.multitenant import create_user_context


def grant_permissions(db: Session, user_tenant, *permission_codes: str):
    """Concede permisos al rol del contexto de prueba."""
    # El caller puede haber creado otro tenant después de crear este
    # user_tenant. Restauramos el contexto correcto antes de consultar o
    # insertar en role_permissions, que está protegido por RLS.
    set_rls_tenant(db, user_tenant.tenant_id)

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

    # Guardamos los IDs antes de cambiar el contexto RLS. grant_permissions()
    # hace expire_all(), por lo que acceder luego a tenant_b.id intentaría
    # recargar el tenant bajo el contexto de tenant A y RLS lo ocultaría.
    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id

    grant_permissions(db_session, user_tenant_a, "TENANT_READ")

    response = client.get(
        f"/tenants/{tenant_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    own_response = client.get(
        f"/tenants/{tenant_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert own_response.status_code == 200
    assert own_response.json()["id"] == tenant_a_id


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

    tenant_a_id = tenant_a.id
    tenant_b_id = tenant_b.id
    original_name = tenant_b.name

    grant_permissions(db_session, user_tenant_a, "TENANT_UPDATE")

    response = client.patch(
        f"/tenants/{tenant_b_id}",
        json={"name": "Tenant comprometido"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    # La sesión de aplicación está bajo el contexto RLS de tenant A, por lo
    # que no puede usarse para comprobar la existencia de tenant B. La
    # verificación de persistencia debe hacerse con la conexión de bootstrap,
    # que tiene BYPASSRLS, sin alterar el comportamiento que estamos probando.
    verification_db = BootstrapSessionLocal()
    try:
        tenant_b_after = verification_db.get(type(tenant_b), tenant_b_id)
        assert tenant_b_after is not None
        assert tenant_b_after.name == original_name
    finally:
        verification_db.close()

    assert tenant_a_id != tenant_b_id


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

    tenant_b_id = tenant_b.id

    grant_permissions(db_session, user_tenant_a, "TENANT_DELETE")

    response = client.delete(
        f"/tenants/{tenant_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant no encontrado"

    verification_db = BootstrapSessionLocal()
    try:
        tenant_b_after = verification_db.get(type(tenant_b), tenant_b_id)
        assert tenant_b_after is not None
        assert tenant_b_after.status == 1
    finally:
        verification_db.close()

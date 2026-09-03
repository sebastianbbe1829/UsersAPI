from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.controllers import global_auth_controller as global_auth
from UsersAPI.controllers import permission_controller as permission
from UsersAPI.controllers import super_tenant_controller as super_tenant
from UsersAPI.controllers import user_controller as user
from UsersAPI.controllers import user_tenant_controller as user_tenant
from UsersAPI.controllers import user_tenant_role_controller as user_role


def test_global_auth_controller_adapters(monkeypatch):
    db = MagicMock()
    datos = SimpleNamespace()
    bootstrap = MagicMock(return_value="bootstrap")
    login = MagicMock(return_value=SimpleNamespace(access_token="jwt"))
    audit = MagicMock()
    decode = MagicMock(return_value={"user_type": "SUPER", "tenant_id": 7})
    monkeypatch.setattr(global_auth, "bootstrap_super_user_service", bootstrap)
    monkeypatch.setattr(global_auth, "login_super_user_service", login)
    monkeypatch.setattr(global_auth, "create_login_session", audit)
    monkeypatch.setattr(global_auth.jwt, "decode", decode)

    assert global_auth.bootstrap_super_user(datos, "secret", db) == "bootstrap"
    bootstrap.assert_called_once_with(datos, "secret", db)

    request = SimpleNamespace(
        client=SimpleNamespace(host="10.0.0.1"),
        headers={"user-agent": "pytest"},
    )
    result = global_auth.login_super_user(datos, request, db)
    assert result.access_token == "jwt"
    login.assert_called_once_with(datos, db, client_ip="10.0.0.1")
    audit.assert_called_once_with(
        db,
        "jwt",
        {"user_type": "SUPER", "tenant_id": 7},
        client_ip="10.0.0.1",
        user_agent="pytest",
    )

    request = SimpleNamespace(client=None, headers={})
    global_auth.login_super_user(datos, request, db)
    assert login.call_args.kwargs["client_ip"] is None


def test_permission_controller_adapters(monkeypatch):
    db = MagicMock()
    datos = SimpleNamespace(code="USER_READ")
    current_user = SimpleNamespace(id=1)
    list_mock = MagicMock(return_value=[1])
    get_mock = MagicMock(return_value=2)
    create_mock = MagicMock(return_value=3)
    monkeypatch.setattr(permission, "list_permission", list_mock)
    monkeypatch.setattr(permission, "get_permission", get_mock)
    monkeypatch.setattr(permission, "create_permission", create_mock)

    assert permission.listar_permisos(db) == [1]
    assert permission.obtener_permiso("USER_READ", db) == 2
    assert permission.crear_permiso(datos, current_user, db) == 3
    list_mock.assert_called_once_with(db=db)
    get_mock.assert_called_once_with(code="USER_READ", db=db)
    create_mock.assert_called_once_with(
        datos=datos, current_user=current_user, db=db
    )


def test_user_controller_adapters(monkeypatch):
    db = MagicMock()
    create = MagicMock(return_value="create")
    listing = MagicMock(return_value="list")
    get = MagicMock(return_value="get")
    update = MagicMock(return_value="update")
    delete = MagicMock(return_value="delete")
    export = MagicMock(return_value="export")
    activate = MagicMock(return_value="activate")
    for name, value in (
        ("create_user", create),
        ("list_users", listing),
        ("get_user", get),
        ("update_user", update),
        ("delete_user", delete),
        ("export_users", export),
        ("activate_user", activate),
    ):
        monkeypatch.setattr(user, name, value)

    current = SimpleNamespace(id=1)
    tenant_user = SimpleNamespace(tenant_id=9)
    datos = SimpleNamespace()
    assert user.crear_usuario(datos, db, current, tenant_user) == "create"
    assert user.listar_usuarios(db, 9, 1) == "list"
    assert user.obtener_usuario("12345", db, tenant_user) == "get"
    assert user.actualizar_usuario(
        "12345", datos, db, current, tenant_user
    ) == "update"
    assert user.eliminar_usuario("12345", db, tenant_user) == "delete"
    assert user.exportar_usuarios(db, current, tenant_user) == "export"
    assert user.activar_usuario("12345", "token", db) == "activate"


def test_user_tenant_and_role_controller_adapters(monkeypatch):
    db = MagicMock()
    list_tenants = MagicMock(return_value=[1])
    assign = MagicMock(return_value="assign")
    list_roles = MagicMock(return_value="roles")
    delete_role = MagicMock(return_value="delete")
    monkeypatch.setattr(user_tenant, "list_user_tenants", list_tenants)
    monkeypatch.setattr(user_role, "assign_role_to_user", assign)
    monkeypatch.setattr(user_role, "list_user_roles", list_roles)
    monkeypatch.setattr(user_role, "delete_user_role", delete_role)

    assert user_tenant.listar_tenants_usuario(4, 9, db) == [1]
    assert user_role.asignar_rol_usuario(4, 7, 9, db) == "assign"
    assert user_role.listar_roles_usuario(4, 9, db) == "roles"
    assert user_role.eliminar_rol_usuario(8, 9, db) == "delete"


def test_super_tenant_controller_adapters(monkeypatch):
    db = MagicMock()
    current = SimpleNamespace(id=1)
    user_obj = SimpleNamespace(id=10)
    datos = SimpleNamespace(name="New")
    require = MagicMock(return_value=user_obj)
    verify = MagicMock()
    listing = MagicMock(return_value=[1])
    getter = MagicMock(return_value=2)
    updater = MagicMock(return_value=3)
    provision = MagicMock(
        return_value={
            "tenant": SimpleNamespace(id=1, name="Acme", slug="acme"),
            "user": SimpleNamespace(id=2, dni="12345", name="Admin"),
            "user_tenant": SimpleNamespace(id=3, email="admin@acme.com"),
            "role": SimpleNamespace(id=4, code="ADMIN", name="Administrador"),
        }
    )
    monkeypatch.setattr(super_tenant, "require_super_user", require)
    monkeypatch.setattr(super_tenant, "verify_super_mfa_otp", verify)
    monkeypatch.setattr(super_tenant, "list_all_tenants", listing)
    monkeypatch.setattr(super_tenant, "get_any_tenant", getter)
    monkeypatch.setattr(super_tenant, "provision_tenant", provision)
    monkeypatch.setattr(super_tenant, "update_any_tenant", updater)

    assert super_tenant.listar_tenants_super(db, current) == [1]
    assert super_tenant.obtener_tenant_super(7, db, current) == 2
    result = super_tenant.crear_tenant_super(SimpleNamespace(), "123", db, current)
    assert result.tenant_id == 1
    assert result.role_code == "ADMIN"
    assert super_tenant.actualizar_tenant_super(
        7, datos, "456", db, current
    ) == 3
    assert verify.call_count == 2
    updater.assert_called_once_with(
        tenant_id=7,
        datos=datos,
        db=db,
        current_user=user_obj,
    )

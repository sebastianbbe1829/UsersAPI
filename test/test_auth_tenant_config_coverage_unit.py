import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException


def test_auth_route_covers_tenant_and_super_login_branches(monkeypatch):
    routes = __import__("UsersAPI.routes.auth_routes", fromlist=["auth_routers"])
    controller = MagicMock()
    limiter = MagicMock()
    monkeypatch.setattr(routes, "auth_controller", controller)
    monkeypatch.setattr(routes, "rate_limiter", limiter)
    limiter.client_ip.return_value = "10.0.0.1"
    limiter.normalize.side_effect = lambda value: value.strip().lower()
    controller.login_user.return_value = "ok"
    db = MagicMock()
    request = SimpleNamespace()
    tenant_data = SimpleNamespace(username="User@EXAMPLE.com", tenant=" Acme ", super_mode=False, otp=None)
    assert routes.login(tenant_data, request, db) == "ok"
    assert limiter.check.call_count == 2
    assert limiter.check.call_args_list[1].args[0] == "login:account:acme:user@example.com"

    limiter.reset_mock()
    super_data = SimpleNamespace(username="Super@EXAMPLE.com", tenant="Acme", super_mode=True, otp="123456")
    assert routes.login(super_data, request, db) == "ok"
    assert limiter.check.call_count == 3
    assert limiter.check.call_args_list[2].args[0] == "login:super:mfa:super@example.com"

    controller.validate_token.return_value = {"valid": True}
    assert routes.validate("jwt", SimpleNamespace(), db) == {"valid": True}
    controller.validate_token.assert_called_once_with("jwt", db)


def test_tenant_config_routes_cover_normal_and_super_paths(monkeypatch):
    routes = __import__("UsersAPI.routes.tenant_config_routes", fromlist=["tenant_config_routes"])
    getter = MagicMock(return_value="get")
    updater = MagicMock(return_value="update")
    require_super = MagicMock(return_value="super")
    verify_mfa = MagicMock()
    repo_instance = MagicMock()
    tenant = SimpleNamespace(id=7)
    repo_instance.get_by_id.return_value = tenant
    monkeypatch.setattr(routes, "obtener_config_tenant", getter)
    monkeypatch.setattr(routes, "actualizar_config_tenant", updater)
    monkeypatch.setattr(routes, "require_super_user", require_super)
    monkeypatch.setattr(routes, "verify_super_mfa_otp", verify_mfa)
    monkeypatch.setattr(routes, "TenantRepository", MagicMock(return_value=repo_instance))

    user_tenant = SimpleNamespace(tenant=tenant)
    current = SimpleNamespace(id=9)
    db = MagicMock()
    datos = SimpleNamespace()
    assert asyncio.run(routes.obtener_config_tenant_route(user_tenant, db)) == "get"
    assert asyncio.run(routes.actualizar_config_tenant_route(datos, user_tenant, current, db)) == "update"
    assert asyncio.run(routes.obtener_config_tenant_super_route(7, db, current)) == "get"
    assert asyncio.run(routes.actualizar_config_tenant_super_route(7, datos, "654321", db, current)) == "update"
    getter.assert_any_call(tenant=tenant, db=db, current_user=user_tenant)
    updater.assert_any_call(tenant=tenant, datos=datos, db=db, current_user=current)
    verify_mfa.assert_called_once_with("super", "654321")

    repo_instance.get_by_id.return_value = None
    with __import__("pytest").raises(HTTPException) as exc:
        asyncio.run(routes.obtener_config_tenant_super_route(99, db, current))
    assert exc.value.status_code == 404

    with __import__("pytest").raises(HTTPException) as exc:
        asyncio.run(routes.actualizar_config_tenant_super_route(99, datos, "654321", db, current))
    assert exc.value.status_code == 404

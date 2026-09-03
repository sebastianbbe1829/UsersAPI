from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.routes import email_routes, global_auth_routes, otp_routes
from UsersAPI.routes import tenant_config_public_routes
from UsersAPI.services import extinguisher_export_service, user_export_service


def test_otp_generate_route_delegates_and_rate_limits(monkeypatch):
    datos = SimpleNamespace(destination=" User@Example.COM ", purpose=" Login ")
    request = SimpleNamespace(client=SimpleNamespace(host="10.0.0.5"))
    db = MagicMock()
    validate = MagicMock()
    create = MagicMock(return_value={"status": "ok"})
    client_ip = MagicMock(return_value="10.0.0.5")
    normalize = MagicMock(side_effect=lambda value: value.strip().lower())
    check = MagicMock()
    monkeypatch.setattr(otp_routes, "validate_otp_api_key", validate)
    monkeypatch.setattr(otp_routes, "create_otp", create)
    monkeypatch.setattr(otp_routes.rate_limiter, "client_ip", client_ip)
    monkeypatch.setattr(otp_routes.rate_limiter, "normalize", normalize)
    monkeypatch.setattr(otp_routes.rate_limiter, "check", check)

    result = otp_routes.create_otp_route(datos, request, db, "secret")

    assert result == {"status": "ok"}
    validate.assert_called_once_with("secret")
    create.assert_called_once_with(datos, db)
    assert check.call_count == 2
    assert check.call_args_list[0].args[0] == "otp:generate:ip:10.0.0.5"
    assert check.call_args_list[1].args[0] == "otp:generate:destination:login:user@example.com"


def test_otp_validate_route_delegates_and_uses_normalized_values(monkeypatch):
    datos = SimpleNamespace(destination=" +57 300 ", purpose=" MFA ")
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    db = MagicMock()
    validate = MagicMock()
    verify = MagicMock(return_value={"valid": True})
    monkeypatch.setattr(otp_routes, "validate_otp_api_key", validate)
    monkeypatch.setattr(otp_routes, "verify_otp", verify)
    monkeypatch.setattr(otp_routes.rate_limiter, "client_ip", lambda request: "127.0.0.1")
    monkeypatch.setattr(otp_routes.rate_limiter, "normalize", lambda value: value.strip().lower())
    check = MagicMock()
    monkeypatch.setattr(otp_routes.rate_limiter, "check", check)

    result = otp_routes.verify_otp_route(datos, request, db, "key")

    assert result == {"valid": True}
    validate.assert_called_once_with("key")
    verify.assert_called_once_with(datos, db)
    assert check.call_args_list[0].args[0] == "otp:validate:ip:127.0.0.1"
    assert check.call_args_list[1].args[0] == "otp:validate:destination:mfa:+57 300"


def test_global_auth_routes_cover_bootstrap_mfa_and_login_without_otp(monkeypatch):
    request = SimpleNamespace(client=SimpleNamespace(host="10.0.0.9"))
    db = MagicMock()
    datos = SimpleNamespace(email=" Admin@Example.COM ", otp=None)
    bootstrap = MagicMock(return_value="boot")
    mfa = MagicMock(return_value="mfa")
    login = MagicMock(return_value="login")
    monkeypatch.setattr(global_auth_routes.global_auth_controller, "bootstrap_super_user", bootstrap)
    monkeypatch.setattr(global_auth_routes.global_auth_bootstrap_controller, "verify_bootstrap_mfa", mfa)
    monkeypatch.setattr(global_auth_routes.global_auth_controller, "login_super_user", login)
    monkeypatch.setattr(global_auth_routes.rate_limiter, "client_ip", lambda request: "10.0.0.9")
    monkeypatch.setattr(global_auth_routes.rate_limiter, "normalize", lambda value: value.strip().lower())
    check = MagicMock()
    monkeypatch.setattr(global_auth_routes.rate_limiter, "check", check)

    assert global_auth_routes.bootstrap_super_user(SimpleNamespace(), request, "secret", db) == "boot"
    assert global_auth_routes.verify_bootstrap_mfa(SimpleNamespace(), request, "secret", db) == "mfa"
    assert global_auth_routes.login_super_user(datos, request, db) == "login"
    bootstrap.assert_called_once()
    mfa.assert_called_once()
    login.assert_called_once_with(datos, request, db)
    assert check.call_count == 4


def test_global_auth_login_route_checks_mfa_when_otp_is_present(monkeypatch):
    request = SimpleNamespace(client=SimpleNamespace(host="10.0.0.10"))
    datos = SimpleNamespace(email="admin@example.com", otp="123456")
    check = MagicMock()
    login = MagicMock(return_value="ok")
    monkeypatch.setattr(global_auth_routes.rate_limiter, "client_ip", lambda request: "10.0.0.10")
    monkeypatch.setattr(global_auth_routes.rate_limiter, "normalize", lambda value: value.lower())
    monkeypatch.setattr(global_auth_routes.rate_limiter, "check", check)
    monkeypatch.setattr(global_auth_routes.global_auth_controller, "login_super_user", login)

    assert global_auth_routes.login_super_user(datos, request, MagicMock()) == "ok"
    assert check.call_args_list[2].args[0] == "super:mfa:admin@example.com"


def test_email_route_rejects_missing_key(monkeypatch):
    monkeypatch.setattr(email_routes.settings, "email_key", None)
    with pytest.raises(HTTPException) as exc:
        email_routes.test_email(SimpleNamespace(recipient="a@b.com", subject="s", message="m"), "key")
    assert exc.value.status_code == 500


def test_email_route_rejects_invalid_key(monkeypatch):
    monkeypatch.setattr(email_routes.settings, "email_key", "expected")
    with pytest.raises(HTTPException) as exc:
        email_routes.test_email(SimpleNamespace(recipient="a@b.com", subject="s", message="m"), "wrong")
    assert exc.value.status_code == 403


def test_email_route_sends_successfully(monkeypatch):
    monkeypatch.setattr(email_routes.settings, "email_key", "expected")
    send = MagicMock(return_value={"message_id": "abc-123"})
    monkeypatch.setattr(email_routes, "send_brevo_email", send)
    datos = SimpleNamespace(recipient="a@b.com", subject="s", message="m")

    result = email_routes.test_email(datos, "expected")

    assert result["status"] == "sent"
    assert result["recipient"] == "a@b.com"
    assert result["message_id"] == "abc-123"
    send.assert_called_once_with(recipient="a@b.com", subject="s", message="m")


def test_email_route_translates_provider_error(monkeypatch):
    monkeypatch.setattr(email_routes.settings, "email_key", "expected")
    monkeypatch.setattr(email_routes, "send_brevo_email", MagicMock(side_effect=RuntimeError("provider down")))

    with pytest.raises(HTTPException) as exc:
        email_routes.test_email(SimpleNamespace(recipient="a@b.com", subject="s", message="m"), "expected")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_public_tenant_config_route_returns_config(monkeypatch):
    tenant = SimpleNamespace(id=7, name="Acme", slug="Acme")
    config = SimpleNamespace(
        app_title="Acme App",
        logo_url="/logo.png",
        primary_color="#123456",
        secondary_color="#654321",
        updated_at=date(2026, 9, 1),
    )
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = tenant
    bootstrap_db = MagicMock()
    bootstrap_db.query.return_value = query
    db = MagicMock()
    repo = MagicMock()
    repo.get_by_tenant_id.return_value = config
    monkeypatch.setattr(tenant_config_public_routes, "TenantConfigRepository", MagicMock(return_value=repo))
    set_rls = MagicMock()
    monkeypatch.setattr(tenant_config_public_routes, "set_rls_tenant", set_rls)

    result = await tenant_config_public_routes.obtener_config_tenant_publica_route("  ACME  ", db, bootstrap_db)

    assert result["tenant_id"] == 7
    assert result["name"] == "Acme"
    assert result["slug"] == "Acme"
    assert result["app_title"] == "Acme App"
    set_rls.assert_called_once_with(db, 7)
    repo.get_by_tenant_id.assert_called_once_with(7)


@pytest.mark.asyncio
async def test_public_tenant_config_route_rejects_missing_tenant():
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = None
    bootstrap_db = MagicMock()
    bootstrap_db.query.return_value = query

    with pytest.raises(HTTPException) as exc:
        await tenant_config_public_routes.obtener_config_tenant_publica_route("unknown", MagicMock(), bootstrap_db)
    assert exc.value.status_code == 404
    assert "tenant activo" in exc.value.detail


@pytest.mark.asyncio
async def test_public_tenant_config_route_rejects_missing_config(monkeypatch):
    tenant = SimpleNamespace(id=7, name="Acme", slug="acme")
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = tenant
    bootstrap_db = MagicMock()
    bootstrap_db.query.return_value = query
    repo = MagicMock()
    repo.get_by_tenant_id.return_value = None
    monkeypatch.setattr(tenant_config_public_routes, "TenantConfigRepository", MagicMock(return_value=repo))
    set_rls = MagicMock()
    monkeypatch.setattr(tenant_config_public_routes, "set_rls_tenant", set_rls)

    with pytest.raises(HTTPException) as exc:
        await tenant_config_public_routes.obtener_config_tenant_publica_route("acme", MagicMock(), bootstrap_db)
    assert exc.value.status_code == 404
    assert "configuración visual" in exc.value.detail
    set_rls.assert_called_once_with(bootstrap_db if False else exc.value, 7) if False else set_rls.assert_called_once()


def test_user_export_service_builds_rows_and_delegates(monkeypatch):
    user = SimpleNamespace(id=1, dni="123", name="Ana")
    link = SimpleNamespace(email="ana@example.com", phone=None, status=1)
    repo = MagicMock()
    repo.get_all_by_tenant.return_value = [user]
    link_repo = MagicMock()
    link_repo.get_by_user_and_tenant.return_value = link
    export = MagicMock(return_value="xlsx")
    monkeypatch.setattr(user_export_service, "UserRepository", MagicMock(return_value=repo))
    monkeypatch.setattr(user_export_service, "UserTenantRepository", MagicMock(return_value=link_repo))
    monkeypatch.setattr(user_export_service, "export_to_excel", export)
    current = SimpleNamespace(id=99)

    assert user_export_service.export_users(MagicMock(), current, 7) == "xlsx"
    export.assert_called_once()
    payload = export.call_args.kwargs["data"]
    assert payload == [{"DNI": "123", "Nombre": "Ana", "Email": "ana@example.com", "Teléfono": "", "Estado": "Activo"}]


def test_user_export_service_raises_when_link_is_missing(monkeypatch):
    user = SimpleNamespace(id=1, dni="123", name="Ana")
    repo = MagicMock()
    repo.get_all_by_tenant.return_value = [user]
    link_repo = MagicMock()
    link_repo.get_by_user_and_tenant.return_value = None
    monkeypatch.setattr(user_export_service, "UserRepository", MagicMock(return_value=repo))
    monkeypatch.setattr(user_export_service, "UserTenantRepository", MagicMock(return_value=link_repo))

    with pytest.raises(HTTPException):
        user_export_service.export_users(MagicMock(), SimpleNamespace(id=99), 7)


def test_extinguisher_export_service_builds_active_and_inactive_rows(monkeypatch):
    inspection = SimpleNamespace(inspection_date=date(2026, 8, 1), result="OK")
    extinguishers = [
        SimpleNamespace(
            id=1, code="E-1", extinguisher_type=SimpleNamespace(name="ABC"), capacity="10 lb",
            location="P1", active=True, is_stock=False, last_recharge_date=None,
            next_recharge_date=None, last_hydrostatic_test_date=None,
            next_hydrostatic_test_date=None, inspections_since_hydrostatic_test=4,
        ),
        SimpleNamespace(
            id=2, code="E-2", extinguisher_type=None, capacity=None, location=None,
            active=False, is_stock=True, last_recharge_date=date(2026, 1, 1),
            next_recharge_date=date(2027, 1, 1), last_hydrostatic_test_date=date(2025, 1, 1),
            next_hydrostatic_test_date=date(2030, 1, 1), inspections_since_hydrostatic_test=None,
        ),
    ]
    repo = MagicMock()
    repo.get_all_by_tenant.return_value = extinguishers
    monkeypatch.setattr(extinguisher_export_service, "ExtinguisherRepository", MagicMock(return_value=repo))
    export = MagicMock(return_value="xlsx")
    monkeypatch.setattr(extinguisher_export_service, "export_extinguishers_to_excel", export)
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.side_effect = [inspection, None]
    db = MagicMock()
    db.query.return_value = query

    assert extinguisher_export_service.export_extinguishers(db, SimpleNamespace(id=99), 7) == "xlsx"
    data = export.call_args.args[0]
    assert len(data) == 2
    assert data[0]["Estado"] == "Activo"
    assert data[0]["Hidrostática requerida"] == "Sí"
    assert data[0]["Última revisión"] == date(2026, 8, 1)
    assert data[1]["Tipo"] == ""
    assert data[1]["Estado"] == "Inactivo"
    assert data[1]["Revisiones desde hidrostática"] == 0
    assert data[1]["Hidrostática requerida"] == "No"

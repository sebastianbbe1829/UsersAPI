from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.exc import IntegrityError

from UsersAPI.controllers import global_user_controller
from UsersAPI.routes import global_user_routes
from UsersAPI.services import account_lock_notification_service as lock_service
from UsersAPI.services import auth_audit_service, user_update_service
from UsersAPI.settings import settings
from UsersAPI.util import email_utils
from UsersAPI.schemas.user import UserUpdate


def test_global_user_controller_adapters_cover_all_paths(monkeypatch):
    db = MagicMock()
    actor = SimpleNamespace(id=1)
    datos = SimpleNamespace()

    require = MagicMock(return_value=actor)
    listing = MagicMock(return_value=[1])
    getter = MagicMock(return_value=2)
    provisioning = MagicMock(return_value=3)
    creator = MagicMock(return_value=4)
    updater = MagicMock(return_value=5)

    monkeypatch.setattr(global_user_controller, "require_super_user", require)
    monkeypatch.setattr(global_user_controller, "list_global_supers", listing)
    monkeypatch.setattr(global_user_controller, "get_global_super", getter)
    monkeypatch.setattr(
        global_user_controller,
        "get_global_super_mfa_provisioning",
        provisioning,
    )
    monkeypatch.setattr(global_user_controller, "create_global_super", creator)
    monkeypatch.setattr(global_user_controller, "update_global_super", updater)

    assert global_user_controller.listar_global_supers(db, actor) == [1]
    assert global_user_controller.obtener_global_super(2, db, actor) == 2
    assert global_user_controller.obtener_global_super_mfa_provisioning(2, db, actor) == 3
    assert global_user_controller.crear_global_super(datos, "123456", db, actor) == 4
    assert global_user_controller.actualizar_global_super(2, datos, "654321", db, actor) == 5

    assert require.call_count == 4
    listing.assert_called_once_with(db, current_user=actor)
    getter.assert_called_once_with(2, db)
    provisioning.assert_called_once_with(2, db)
    creator.assert_called_once_with(datos=datos, otp="123456", db=db, actor=actor)
    updater.assert_called_once_with(
        super_id=2,
        datos=datos,
        otp="654321",
        db=db,
        current_user=actor,
    )


def test_global_user_routes_cover_all_controller_delegations(monkeypatch):
    db = MagicMock()
    current = SimpleNamespace(id=1)
    datos = SimpleNamespace()

    controller = global_user_routes.global_user_controller
    listar = MagicMock(return_value=[1])
    obtener = MagicMock(return_value=2)
    provisioning = MagicMock(return_value=3)
    crear = MagicMock(return_value=4)
    actualizar = MagicMock(return_value=5)

    monkeypatch.setattr(controller, "listar_global_supers", listar)
    monkeypatch.setattr(controller, "obtener_global_super", obtener)
    monkeypatch.setattr(controller, "obtener_global_super_mfa_provisioning", provisioning)
    monkeypatch.setattr(controller, "crear_global_super", crear)
    monkeypatch.setattr(controller, "actualizar_global_super", actualizar)

    assert global_user_routes.listar_global_supers_route(db=db, current_user=current) == [1]
    assert global_user_routes.obtener_global_super_route(2, db=db, current_user=current) == 2
    assert (
        global_user_routes.obtener_global_super_mfa_provisioning_route(
            2, db=db, current_user=current
        )
        == 3
    )
    assert (
        global_user_routes.crear_global_super_route(
            datos, x_super_mfa_otp="123456", db=db, current_user=current
        )
        == 4
    )
    assert (
        global_user_routes.actualizar_global_super_route(
            2,
            datos,
            x_super_mfa_otp="654321",
            db=db,
            current_user=current,
        )
        == 5
    )

    listar.assert_called_once_with(db=db, current_user=current)
    obtener.assert_called_once_with(super_id=2, db=db, current_user=current)
    provisioning.assert_called_once_with(super_id=2, db=db, current_user=current)
    crear.assert_called_once_with(
        datos=datos,
        otp="123456",
        db=db,
        current_user=current,
    )
    actualizar.assert_called_once_with(
        super_id=2,
        datos=datos,
        otp="654321",
        db=db,
        current_user=current,
    )


def test_account_lock_notification_resolves_admin_recipients_and_sends(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [
        " admin@example.com ",
        None,
        "",
        "second@example.com",
    ]

    assert lock_service._get_admin_recipients(db, 7) == [
        "admin@example.com",
        "second@example.com",
    ]

    send_email = MagicMock()
    monkeypatch.setattr(lock_service, "send_email", send_email)
    lock_service.notify_tenant_admins_account_locked(
        db,
        tenant_id=7,
        tenant_name="Acme",
        user_name="Ana",
        user_login="ana@example.com",
        failed_attempts=5,
    )

    assert send_email.call_count == 2
    assert send_email.call_args_list[0].kwargs["recipient"] == "admin@example.com"
    assert send_email.call_args_list[0].kwargs["template"] == "default"
    assert "5 intentos" in send_email.call_args_list[0].kwargs["message"]


def test_account_lock_notification_handles_no_admins_and_email_failure(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    send_email = MagicMock(side_effect=RuntimeError("mail down"))
    monkeypatch.setattr(lock_service, "send_email", send_email)

    lock_service.notify_tenant_admins_account_locked(
        db,
        tenant_id=7,
        tenant_name="Acme",
        user_name="Ana",
        user_login="ana@example.com",
        failed_attempts=4,
    )
    send_email.assert_not_called()

    db.execute.return_value.scalars.return_value.all.return_value = ["admin@example.com"]
    lock_service.notify_tenant_admins_account_locked(
        db,
        tenant_id=7,
        tenant_name="Acme",
        user_name="Ana",
        user_login="ana@example.com",
        failed_attempts=4,
    )
    send_email.assert_called_once()


def _audit_token(payload):
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def test_auth_audit_covers_user_mapping_super_session_and_close_validation(monkeypatch):
    db = MagicMock()
    user = SimpleNamespace(dni="12345")
    user_tenant = SimpleNamespace(id=8, email="user@example.com", user=user)

    audit = auth_audit_service.audit_auth_event(
        db,
        tenant_id=7,
        event_type=auth_audit_service.LOGIN_FAILED,
        user_tenant=user_tenant,
        actor_login=None,
        actor_dni=None,
        occurred_at=datetime(2026, 9, 4, 10, 0),
    )
    assert audit.user_tenant_id == 8
    assert audit.actor_login == "user@example.com"
    assert audit.actor_dni == "12345"
    assert audit.actor_identifier == "12345"

    payload = {
        "tenant_id": 7,
        "user_tenant_id": None,
        "global_user_id": 99,
        "user_type": auth_audit_service.SUPER_SESSION_KIND,
        "email": "super@example.com",
        "sub": "super@example.com",
    }
    monkeypatch.setattr(auth_audit_service, "set_rls_tenant", MagicMock())
    monkeypatch.setattr(
        auth_audit_service,
        "_now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 5)),
    )
    session = auth_audit_service.create_login_session(db, "token-super", payload)
    assert session.session_kind == "SUPER"
    assert session.global_user_id == 99
    assert session.user_tenant_id is None

    with pytest.raises(ValueError, match="Tipo de evento"):
        auth_audit_service.close_login_session(
            db,
            _audit_token(
                {
                    "tenant_id": 7,
                    "session_id": "s1",
                    "sub": "123",
                }
            ),
            event_type="INVALID",
        )

    assert (
        auth_audit_service.close_login_session(
            db,
            _audit_token({"tenant_id": 7}),
        )
        is None
    )


def test_auth_audit_touch_active_session_and_refresh_success(monkeypatch):
    db = MagicMock()
    session = SimpleNamespace(
        id="session-1",
        tenant_id=7,
        user_tenant_id=8,
        session_kind="TENANT",
        last_activity_at=datetime(2026, 9, 4, 10, 0),
        login_at=datetime(2026, 9, 4, 9, 50),
        client_ip="old",
        user_agent="old-agent",
        global_user_id=None,
        status="ACTIVE",
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = session
    db.query.return_value = query

    now_values = iter(
        [
            datetime(2026, 9, 4, 10, 3),
            datetime(2026, 9, 4, 10, 4),
        ]
    )
    monkeypatch.setattr(auth_audit_service, "_now", lambda: next(now_values))
    monkeypatch.setattr(auth_audit_service, "set_rls_tenant", MagicMock())
    monkeypatch.setattr(
        auth_audit_service.settings,
        "session_idle_timeout_minutes",
        15,
    )

    payload = {
        "tenant_id": 7,
        "session_id": "session-1",
        "user_tenant_id": 8,
        "sub": "123",
        "user_type": "TENANT",
    }
    touched = auth_audit_service.touch_active_session(db, "token", payload)
    assert touched is session
    assert session.last_activity_at == datetime(2026, 9, 4, 10, 3)

    monkeypatch.setattr(
        auth_audit_service,
        "_decode_token",
        MagicMock(return_value=payload),
    )
    monkeypatch.setattr(
        auth_audit_service,
        "_now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 4)),
    )
    monkeypatch.setattr(
        auth_audit_service,
        "create_access_token",
        MagicMock(return_value="new-token"),
    )
    monkeypatch.setattr(auth_audit_service, "audit_auth_event", MagicMock())

    refreshed = auth_audit_service.refresh_login_session(
        db,
        "token",
        client_ip="new-ip",
        user_agent="new-agent",
    )
    assert refreshed["access_token"] == "new-token"
    assert refreshed["token_type"] == "bearer"
    assert refreshed["session_id"] == "session-1"
    assert session.client_ip == "new-ip"
    assert session.user_agent == "new-agent"


def test_auth_audit_idle_timeout_closes_session_and_clears_global_session(monkeypatch):
    db = MagicMock()
    session = SimpleNamespace(
        id="session-idle",
        tenant_id=7,
        user_tenant_id=None,
        global_user_id=50,
        session_kind="SUPER",
        login_at=datetime(2026, 9, 4, 9, 0),
        last_activity_at=datetime(2026, 9, 4, 9, 0),
        status="ACTIVE",
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = session
    db.query.return_value = query
    db.get.return_value = SimpleNamespace(session_id="session-idle")

    monkeypatch.setattr(auth_audit_service, "set_rls_tenant", MagicMock())
    monkeypatch.setattr(
        auth_audit_service,
        "_now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 0)),
    )
    monkeypatch.setattr(
        auth_audit_service.settings,
        "session_idle_timeout_minutes",
        15,
    )
    monkeypatch.setattr(auth_audit_service, "audit_auth_event", MagicMock())

    payload = {
        "tenant_id": 7,
        "session_id": "session-idle",
        "global_user_id": 50,
        "user_type": "SUPER",
        "email": "super@example.com",
    }

    with pytest.raises(HTTPException) as exc_info:
        auth_audit_service.touch_active_session(db, "token", payload)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "La sesión expiró por inactividad"
    assert session.status == "CLOSED"
    assert session.close_reason == auth_audit_service.IDLE_TIMEOUT
    assert db.get.return_value.session_id is None


def test_user_update_covers_unlock_and_all_update_notifications(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=7, slug="acme", name="Acme")
    user = SimpleNamespace(id=11, dni="12345", name="Ana", updated_at=None, updated_by=None)
    link = SimpleNamespace(
        id=21,
        tenant_id=7,
        email="ana@example.com",
        phone="3001234567",
        status=1,
        failed_login_attempts=4,
        last_failed_login_at=datetime(2026, 9, 4, 9, 0),
        locked_at=datetime(2026, 9, 4, 9, 0),
        locked_ip="10.0.0.1",
        updated_at=None,
        updated_by=None,
    )

    user_repo = MagicMock()
    user_repo.get_by_dni_in_tenant.return_value = user
    tenant_repo = MagicMock()
    tenant_repo.get_by_id.return_value = tenant
    link_repo = MagicMock()
    link_repo.get_by_user_and_tenant.return_value = link

    monkeypatch.setattr(user_update_service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(user_update_service, "UserTenantRepository", lambda db: link_repo)
    monkeypatch.setattr(user_update_service, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(user_update_service, "_actor_dni", lambda _: "actor")
    monkeypatch.setattr(user_update_service, "get_password_hash", lambda value: f"hash:{value}")
    monkeypatch.setattr(user_update_service, "audit_auth_event", MagicMock())
    monkeypatch.setattr(user_update_service, "send_email", MagicMock())
    monkeypatch.setattr(user_update_service, "send_whatsapp", MagicMock())
    monkeypatch.setattr(
        user_update_service.datetime,
        "now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 0)),
    )

    current = SimpleNamespace(email="actor@example.com")
    datos = UserUpdate(
        name="Ana Updated",
        email="new@example.com",
        phone="3007654321",
        password="NewPassword123",
        status=0,
        unlock=True,
    )

    result = user_update_service.update_user(
        "12345",
        datos,
        db,
        current,
        link,
    )

    assert result["name"] == "Ana Updated"
    assert result["email"] == "new@example.com"
    assert result["phone"] == "3007654321"
    assert result["status"] == 0
    assert link.failed_login_attempts == 0
    assert link.last_failed_login_at is None
    assert link.locked_at is None
    assert link.locked_ip is None
    assert link.password == "hash:NewPassword123"
    user_repo.update.assert_called_once_with(user)
    link_repo.update.assert_called_once_with(link)
    user_update_service.send_email.assert_called_once()
    user_update_service.send_whatsapp.assert_called_once()


def test_user_update_covers_tenant_missing_user_and_link_missing(monkeypatch):
    db = MagicMock()
    tenant_repo = MagicMock()
    user_repo = MagicMock()
    link_repo = MagicMock()
    monkeypatch.setattr(user_update_service, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(user_update_service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(user_update_service, "UserTenantRepository", lambda db: link_repo)

    link_user = SimpleNamespace(tenant_id=7)
    tenant_repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        user_update_service.update_user(
            "1", UserUpdate(name="Ana"), db, SimpleNamespace(), link_user
        )
    assert exc_info.value.status_code == 404

    tenant_repo.get_by_id.return_value = SimpleNamespace(id=7, slug="acme", name="Acme")
    user_repo.get_by_dni_in_tenant.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        user_update_service.update_user(
            "1", UserUpdate(name="Ana"), db, SimpleNamespace(), link_user
        )
    assert exc_info.value.status_code == 404

    user_repo.get_by_dni_in_tenant.return_value = SimpleNamespace(id=1, dni="1", name="Ana")
    link_repo.get_by_user_and_tenant.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        user_update_service.update_user(
            "1", UserUpdate(name="Ana"), db, SimpleNamespace(), link_user
        )
    assert exc_info.value.status_code == 404


def test_user_update_covers_unlock_rejection_integrity_generic_and_notification_failures(monkeypatch):
    db = MagicMock()
    tenant = SimpleNamespace(id=7, slug="acme", name="Acme")
    user = SimpleNamespace(id=1, dni="1", name="Ana")
    link = SimpleNamespace(
        id=2,
        tenant_id=7,
        email="ana@example.com",
        phone="3001234567",
        status=1,
        failed_login_attempts=1,
        last_failed_login_at=datetime(2026, 9, 4, 9, 0),
        locked_at=None,
        locked_ip=None,
    )
    tenant_repo = MagicMock()
    tenant_repo.get_by_id.return_value = tenant
    user_repo = MagicMock()
    user_repo.get_by_dni_in_tenant.return_value = user
    link_repo = MagicMock()
    link_repo.get_by_user_and_tenant.return_value = link
    monkeypatch.setattr(user_update_service, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(user_update_service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(user_update_service, "UserTenantRepository", lambda db: link_repo)
    monkeypatch.setattr(user_update_service, "_actor_dni", lambda _: "actor")
    monkeypatch.setattr(user_update_service, "audit_auth_event", MagicMock())

    with pytest.raises(HTTPException) as exc_info:
        user_update_service.update_user(
            "1", UserUpdate(unlock=True), db, SimpleNamespace(email="a@b"), link
        )
    assert exc_info.value.status_code == 409

    link.locked_at = datetime(2026, 9, 4, 9, 0)
    user_repo.update.side_effect = IntegrityError("stmt", {}, Exception("duplicate"))
    with pytest.raises(HTTPException) as exc_info:
        user_update_service.update_user(
            "1", UserUpdate(name="Changed"), db, SimpleNamespace(email="a@b"), link
        )
    assert exc_info.value.status_code == 400

    user_repo.update.side_effect = RuntimeError("database down")
    with pytest.raises(HTTPException) as exc_info:
        user_update_service.update_user(
            "1", UserUpdate(name="Changed"), db, SimpleNamespace(email="a@b"), link
        )
    assert exc_info.value.status_code == 500

    user_repo.update.side_effect = None
    link_repo.update.side_effect = None
    email = MagicMock(side_effect=RuntimeError("mail"))
    whatsapp = MagicMock(side_effect=RuntimeError("wa"))
    monkeypatch.setattr(user_update_service, "send_email", email)
    monkeypatch.setattr(user_update_service, "send_whatsapp", whatsapp)
    result = user_update_service.update_user(
        "1", UserUpdate(name="Changed"), db, SimpleNamespace(email="a@b"), link
    )
    assert result["name"] == "Changed"
    email.assert_called_once()
    whatsapp.assert_called_once()

    link.phone = None
    email.reset_mock()
    whatsapp.reset_mock()
    user_update_service.update_user(
        "1", UserUpdate(name="Changed Again"), db, SimpleNamespace(email="a@b"), link
    )
    whatsapp.assert_not_called()


def _configure_email(monkeypatch):
    monkeypatch.setattr(email_utils, "BREVO_API_KEY", "key")
    monkeypatch.setattr(email_utils, "EMAIL_FROM", "from@test")
    monkeypatch.setattr(email_utils, "EMAIL_FROM_NAME", "App")
    monkeypatch.setattr(email_utils, "BACKEND_URL", "https://backend/")
    monkeypatch.setattr(email_utils, "FRONTEND_URL", "https://front/")
    monkeypatch.setattr(email_utils, "API_EMAIL_URL", "https://brevo")
    monkeypatch.setattr(email_utils.os.path, "isfile", lambda _: True)
    template = MagicMock()
    template.render.return_value = "<html>ok</html>"
    monkeypatch.setattr(email_utils.env, "get_template", lambda _: template)
    return template


def test_email_coverage_hits_configuration_and_activation_validation(monkeypatch):
    _configure_email(monkeypatch)

    monkeypatch.setattr(email_utils, "EMAIL_FROM", "")
    with pytest.raises(RuntimeError, match="EMAIL_FROM"):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils, "BACKEND_URL", "")
    with pytest.raises(RuntimeError, match="BACKEND_URL"):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils, "FRONTEND_URL", "")
    with pytest.raises(RuntimeError, match="FRONTEND_URL"):
        email_utils.send_email(
            "a@b", "s", "m", template="activation", tenant_slug="acme", dni="1", token="t"
        )

    _configure_email(monkeypatch)
    with pytest.raises(RuntimeError, match="tenant_slug"):
        email_utils.send_email(
            "a@b", "UsersAPI activation", "m", template="activation", dni="1", token="t"
        )

    _configure_email(monkeypatch)
    with pytest.raises(RuntimeError, match="dni"):
        email_utils.send_email(
            "a@b", "UsersAPI activation", "m", template="activation", tenant_slug="acme", token="t"
        )

    _configure_email(monkeypatch)
    with pytest.raises(RuntimeError, match="token"):
        email_utils.send_email(
            "a@b", "UsersAPI activation", "m", template="activation", tenant_slug="acme", dni="1"
        )

    _configure_email(monkeypatch)
    with pytest.raises(RuntimeError, match="tenant_slug"):
        email_utils.send_email("a@b", "UsersAPI updated", "m", template="updated")


def test_email_coverage_hits_template_render_and_request_error(monkeypatch):
    template = _configure_email(monkeypatch)
    template.render.side_effect = ValueError("render error")
    with pytest.raises(ValueError, match="render error"):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    response = MagicMock(status_code=400, text="bad")
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("bad request")
    monkeypatch.setattr(email_utils.requests, "post", MagicMock(return_value=response))
    with pytest.raises(requests.exceptions.HTTPError):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    monkeypatch.setattr(
        email_utils.requests,
        "post",
        MagicMock(side_effect=requests.exceptions.RequestException("network")),
    )
    with pytest.raises(requests.exceptions.RequestException):
        email_utils.send_email("a@b", "s", "m")

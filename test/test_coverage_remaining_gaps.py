from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.exc import IntegrityError

from UsersAPI.controllers import global_user_controller
import UsersAPI.routes.global_user_routes as global_user_routes
from UsersAPI.schemas.user import UserUpdate
from UsersAPI.services import account_lock_notification_service as lock_service
from UsersAPI.services import auth_audit_service, user_update_service
from UsersAPI.settings import settings
from UsersAPI.util import email_utils


def test_global_user_controller_adapters(monkeypatch):
    db = MagicMock()
    actor = SimpleNamespace(id=1)
    data = SimpleNamespace()
    require = MagicMock(return_value=actor)
    mocks = {
        "list_global_supers": MagicMock(return_value=[1]),
        "get_global_super": MagicMock(return_value=2),
        "get_global_super_mfa_provisioning": MagicMock(return_value=3),
        "create_global_super": MagicMock(return_value=4),
        "update_global_super": MagicMock(return_value=5),
    }
    monkeypatch.setattr(global_user_controller, "require_super_user", require)
    for name, value in mocks.items():
        monkeypatch.setattr(global_user_controller, name, value)

    assert global_user_controller.listar_global_supers(db, actor) == [1]
    assert global_user_controller.obtener_global_super(2, db, actor) == 2
    assert global_user_controller.obtener_global_super_mfa_provisioning(2, db, actor) == 3
    assert global_user_controller.crear_global_super(data, "123456", db, actor) == 4
    assert global_user_controller.actualizar_global_super(2, data, "654321", db, actor) == 5
    assert require.call_count == 4


def test_global_user_routes_delegate_all_paths(monkeypatch):
    db = MagicMock()
    current = SimpleNamespace(id=1)
    data = SimpleNamespace()
    controller = global_user_routes.global_user_controller
    funcs = {
        "listar_global_supers": MagicMock(return_value=[1]),
        "obtener_global_super": MagicMock(return_value=2),
        "obtener_global_super_mfa_provisioning": MagicMock(return_value=3),
        "crear_global_super": MagicMock(return_value=4),
        "actualizar_global_super": MagicMock(return_value=5),
    }
    for name, value in funcs.items():
        monkeypatch.setattr(controller, name, value)

    assert global_user_routes.listar_global_supers_route(
        db=db, current_user=current
    ) == [1]
    assert global_user_routes.obtener_global_super_route(
        2, db=db, current_user=current
    ) == 2
    assert global_user_routes.obtener_global_super_mfa_provisioning_route(
        2, db=db, current_user=current
    ) == 3
    assert global_user_routes.crear_global_super_route(
        data, "123456", db=db, current_user=current
    ) == 4
    assert global_user_routes.actualizar_global_super_route(
        2, data, "654321", db=db, current_user=current
    ) == 5


def test_account_lock_notification_recipient_resolution_and_delivery(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [
        " admin@example.com ", None, "", "second@example.com"
    ]
    assert lock_service._get_admin_recipients(db, 7) == [
        "admin@example.com",
        "second@example.com",
    ]

    send = MagicMock()
    monkeypatch.setattr(lock_service, "send_email", send)
    lock_service.notify_tenant_admins_account_locked(
        db,
        tenant_id=7,
        tenant_name="Acme",
        user_name="Ana",
        user_login="ana@example.com",
        failed_attempts=5,
    )
    assert send.call_count == 2
    assert send.call_args_list[0].kwargs["template"] == "default"
    assert "5 intentos" in send.call_args_list[0].kwargs["message"]


def test_account_lock_notification_handles_no_admins_and_send_failure(monkeypatch):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = []
    send = MagicMock(side_effect=RuntimeError("mail"))
    monkeypatch.setattr(lock_service, "send_email", send)
    lock_service.notify_tenant_admins_account_locked(
        db,
        tenant_id=7,
        tenant_name="Acme",
        user_name="Ana",
        user_login="ana@example.com",
        failed_attempts=4,
    )
    send.assert_not_called()

    db.execute.return_value.scalars.return_value.all.return_value = [
        "admin@example.com"
    ]
    lock_service.notify_tenant_admins_account_locked(
        db,
        tenant_id=7,
        tenant_name="Acme",
        user_name="Ana",
        user_login="ana@example.com",
        failed_attempts=4,
    )
    send.assert_called_once()


def _token(payload):
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def test_auth_audit_maps_user_and_covers_super_and_close_validation(monkeypatch):
    db = MagicMock()
    user_tenant = SimpleNamespace(
        id=8,
        email="user@example.com",
        user=SimpleNamespace(dni="12345"),
    )
    audit = auth_audit_service.audit_auth_event(
        db,
        tenant_id=7,
        event_type=auth_audit_service.LOGIN_FAILED,
        user_tenant=user_tenant,
        occurred_at=datetime(2026, 9, 4, 10, 0),
    )
    assert audit.user_tenant_id == 8
    assert audit.actor_login == "user@example.com"
    assert audit.actor_dni == "12345"
    assert audit.actor_identifier == "12345"

    monkeypatch.setattr(auth_audit_service, "set_rls_tenant", MagicMock())
    monkeypatch.setattr(
        auth_audit_service,
        "_now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 5)),
    )
    session = auth_audit_service.create_login_session(
        db,
        "token",
        {
            "tenant_id": 7,
            "global_user_id": 99,
            "user_type": "SUPER",
            "email": "super@example.com",
        },
    )
    assert session.session_kind == "SUPER"
    assert session.global_user_id == 99

    with pytest.raises(ValueError, match="Tipo de evento"):
        auth_audit_service.close_login_session(
            db,
            _token({"tenant_id": 7, "session_id": "s1"}),
            event_type="INVALID",
        )
    assert auth_audit_service.close_login_session(
        db, _token({"tenant_id": 7})
    ) is None


def test_auth_audit_refresh_and_touch_success(monkeypatch):
    db = MagicMock()
    session = SimpleNamespace(
        id="s1",
        tenant_id=7,
        user_tenant_id=8,
        session_kind="TENANT",
        last_activity_at=datetime(2026, 9, 4, 10, 0),
        login_at=datetime(2026, 9, 4, 9, 50),
        status="ACTIVE",
        client_ip="old",
        user_agent="old",
        global_user_id=None,
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = session
    db.query.return_value = query
    monkeypatch.setattr(auth_audit_service, "set_rls_tenant", MagicMock())
    monkeypatch.setattr(
        auth_audit_service,
        "_now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 3)),
    )
    payload = {
        "tenant_id": 7,
        "session_id": "s1",
        "user_tenant_id": 8,
        "sub": "123",
        "user_type": "TENANT",
    }

    assert auth_audit_service.touch_active_session(db, "token", payload) is session

    monkeypatch.setattr(
        auth_audit_service, "_decode_token", MagicMock(return_value=payload)
    )
    monkeypatch.setattr(
        auth_audit_service,
        "create_access_token",
        MagicMock(return_value="new-token"),
    )
    monkeypatch.setattr(auth_audit_service, "audit_auth_event", MagicMock())
    result = auth_audit_service.refresh_login_session(
        db, "token", client_ip="new", user_agent="agent"
    )
    assert result == {
        "access_token": "new-token",
        "token_type": "bearer",
        "session_id": "s1",
    }
    assert session.client_ip == "new"
    assert session.user_agent == "agent"


def test_auth_audit_idle_timeout_closes_and_clears_super_session(monkeypatch):
    db = MagicMock()
    session = SimpleNamespace(
        id="idle",
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
    db.get.return_value = SimpleNamespace(session_id="idle")
    monkeypatch.setattr(auth_audit_service, "set_rls_tenant", MagicMock())
    monkeypatch.setattr(auth_audit_service, "audit_auth_event", MagicMock())
    monkeypatch.setattr(
        auth_audit_service,
        "_now",
        MagicMock(return_value=datetime(2026, 9, 4, 10, 0)),
    )
    payload = {
        "tenant_id": 7,
        "session_id": "idle",
        "global_user_id": 50,
        "user_type": "SUPER",
        "email": "s@x",
    }
    with pytest.raises(HTTPException) as exc:
        auth_audit_service.touch_active_session(db, "token", payload)
    assert exc.value.detail == "La sesión expiró por inactividad"
    assert session.status == "CLOSED"
    assert db.get.return_value.session_id is None


def _user_update_context(monkeypatch, *, locked=True):
    tenant = SimpleNamespace(id=7, slug="acme", name="Acme")
    user = SimpleNamespace(
        id=11, dni="12345", name="Ana", updated_at=None, updated_by=None
    )
    link = SimpleNamespace(
        id=21,
        tenant_id=7,
        email="ana@example.com",
        phone="3001234567",
        status=1,
        failed_login_attempts=4,
        last_failed_login_at=datetime(2026, 9, 4, 9, 0),
        locked_at=datetime(2026, 9, 4, 9, 0) if locked else None,
        locked_ip="10.0.0.1",
        updated_at=None,
        updated_by=None,
    )
    db = MagicMock()
    tenant_repo, user_repo, link_repo = MagicMock(), MagicMock(), MagicMock()
    tenant_repo.get_by_id.return_value = tenant
    user_repo.get_by_dni_in_tenant.return_value = user
    link_repo.get_by_user_and_tenant.return_value = link
    monkeypatch.setattr(user_update_service, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(user_update_service, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(user_update_service, "UserTenantRepository", lambda db: link_repo)
    monkeypatch.setattr(user_update_service, "_actor_dni", lambda _: "actor")
    return db, user, link, tenant_repo, user_repo, link_repo


def test_user_update_covers_all_mutations_and_notifications(monkeypatch):
    db, user, link, _, user_repo, link_repo = _user_update_context(monkeypatch)
    monkeypatch.setattr(
        user_update_service, "get_password_hash", lambda value: f"hash:{value}"
    )
    monkeypatch.setattr(user_update_service, "audit_auth_event", MagicMock())
    email, whatsapp = MagicMock(), MagicMock()
    monkeypatch.setattr(user_update_service, "send_email", email)
    monkeypatch.setattr(user_update_service, "send_whatsapp", whatsapp)
    current = SimpleNamespace(email="actor@example.com")
    result = user_update_service.update_user(
        "12345",
        UserUpdate(
            name="Ana Updated",
            email="new@example.com",
            phone="3007654321",
            password="NewPassword123",
            status=0,
            unlock=True,
        ),
        db,
        current,
        link,
    )
    assert result["name"] == "Ana Updated"
    assert link.password == "hash:NewPassword123"
    assert link.locked_at is None
    assert link.failed_login_attempts == 0
    user_repo.update.assert_called_once_with(user)
    link_repo.update.assert_called_once_with(link)
    email.assert_called_once()
    whatsapp.assert_called_once()


def test_user_update_covers_lookup_unlock_and_persistence_errors(monkeypatch):
    db, _, link, tenant_repo, user_repo, link_repo = _user_update_context(
        monkeypatch, locked=False
    )
    context = SimpleNamespace(tenant_id=7)
    tenant_repo.get_by_id.return_value = None
    with pytest.raises(HTTPException) as exc:
        user_update_service.update_user(
            "1", UserUpdate(name="Ana"), db, SimpleNamespace(), link
        )
    assert exc.value.status_code == 404

    tenant_repo.get_by_id.return_value = SimpleNamespace(
        id=7, slug="acme", name="Acme"
    )
    user_repo.get_by_dni_in_tenant.return_value = None
    with pytest.raises(HTTPException):
        user_update_service.update_user(
            "1", UserUpdate(name="Ana"), db, SimpleNamespace(), context
        )

    user_repo.get_by_dni_in_tenant.return_value = SimpleNamespace(
        id=1, dni="1", name="Ana"
    )
    link_repo.get_by_user_and_tenant.return_value = None
    with pytest.raises(HTTPException):
        user_update_service.update_user(
            "1", UserUpdate(name="Ana"), db, SimpleNamespace(), context
        )

    link_repo.get_by_user_and_tenant.return_value = link
    link.locked_at = None
    with pytest.raises(HTTPException) as exc:
        user_update_service.update_user(
            "1", UserUpdate(unlock=True), db, SimpleNamespace(email="a@b"), context
        )
    assert exc.value.status_code == 409

    user_repo.update.side_effect = IntegrityError(
        "stmt", {}, Exception("duplicate")
    )
    with pytest.raises(HTTPException) as exc:
        user_update_service.update_user(
            "1", UserUpdate(name="Changed"), db, SimpleNamespace(email="a@b"), context
        )
    assert exc.value.status_code == 400

    user_repo.update.side_effect = RuntimeError("db")
    with pytest.raises(HTTPException) as exc:
        user_update_service.update_user(
            "1", UserUpdate(name="Changed"), db, SimpleNamespace(email="a@b"), context
        )
    assert exc.value.status_code == 500


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


def test_email_configuration_validation_branches(monkeypatch):
    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils, "EMAIL_FROM", "")
    with pytest.raises(RuntimeError, match="EMAIL_FROM"):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils, "BACKEND_URL", "")
    with pytest.raises(RuntimeError, match="BACKEND_URL"):
        email_utils.send_email("a@b", "s", "m")

    for kwargs, field in [
        (
            {
                "template": "activation",
                "tenant_slug": "acme",
                "dni": "1",
                "token": "t",
            },
            "FRONTEND_URL",
        ),
        ({"template": "activation", "dni": "1", "token": "t"}, "tenant_slug"),
        ({"template": "activation", "tenant_slug": "acme", "token": "t"}, "dni"),
        ({"template": "activation", "tenant_slug": "acme", "dni": "1"}, "token"),
        ({"template": "updated"}, "tenant_slug"),
    ]:
        _configure_email(monkeypatch)
        if field == "FRONTEND_URL":
            monkeypatch.setattr(email_utils, "FRONTEND_URL", "")
        with pytest.raises(RuntimeError, match=field):
            email_utils.send_email("a@b", "UsersAPI", "m", **kwargs)


def test_email_template_and_http_exception_branches(monkeypatch):
    template = _configure_email(monkeypatch)
    template.render.side_effect = ValueError("render")
    with pytest.raises(ValueError, match="render"):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils.os.path, "isfile", lambda _: False)
    with pytest.raises(RuntimeError, match="template not found"):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    response = MagicMock(status_code=400, text="bad")
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("bad")
    monkeypatch.setattr(
        email_utils.requests, "post", MagicMock(return_value=response)
    )
    with pytest.raises(requests.exceptions.HTTPError):
        email_utils.send_email("a@b", "s", "m")

    _configure_email(monkeypatch)
    monkeypatch.setattr(
        email_utils.requests,
        "post",
        MagicMock(side_effect=requests.exceptions.RequestException("down")),
    )
    with pytest.raises(requests.exceptions.RequestException):
        email_utils.send_email("a@b", "s", "m")

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import JWTError

from UsersAPI.controllers import activation_otp_controller, auth_controller
from UsersAPI import database


def test_activation_otp_controller_success_and_value_error(monkeypatch):
    expires_at = datetime(2026, 9, 3, 1, 0, 0)
    monkeypatch.setattr(
        activation_otp_controller,
        "generate_activation_otp",
        MagicMock(return_value=expires_at),
    )
    result = activation_otp_controller.request_activation_otp(
        "123", "token", MagicMock()
    )
    assert result.message.startswith("Código de verificación")
    assert result.expires_at == expires_at

    monkeypatch.setattr(
        activation_otp_controller,
        "generate_activation_otp",
        MagicMock(side_effect=ValueError("bad token")),
    )
    with pytest.raises(HTTPException) as exc:
        activation_otp_controller.request_activation_otp(
            "123", "token", MagicMock()
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "bad token"


def test_activation_otp_controller_preserves_http_and_maps_generic_error(monkeypatch):
    http_error = HTTPException(status_code=409, detail="already used")
    monkeypatch.setattr(
        activation_otp_controller,
        "generate_activation_otp",
        MagicMock(side_effect=http_error),
    )
    with pytest.raises(HTTPException) as exc:
        activation_otp_controller.request_activation_otp(
            "123", "token", MagicMock()
        )
    assert exc.value is http_error

    monkeypatch.setattr(
        activation_otp_controller,
        "generate_activation_otp",
        MagicMock(side_effect=RuntimeError("provider")),
    )
    with pytest.raises(HTTPException) as exc:
        activation_otp_controller.request_activation_otp(
            "123", "token", MagicMock()
        )
    assert exc.value.status_code == 502


def test_activation_otp_controller_validation_messages(monkeypatch):
    monkeypatch.setattr(
        activation_otp_controller,
        "validate_activation_otp",
        MagicMock(return_value=True),
    )
    valid = activation_otp_controller.verify_activation_otp(
        "123", "token", SimpleNamespace(code="111111"), MagicMock()
    )
    assert valid.valid is True
    assert "activada" in valid.message

    monkeypatch.setattr(
        activation_otp_controller,
        "validate_activation_otp",
        MagicMock(return_value=False),
    )
    invalid = activation_otp_controller.verify_activation_otp(
        "123", "token", SimpleNamespace(code="000000"), MagicMock()
    )
    assert invalid.valid is False
    assert "inválido" in invalid.message


def test_auth_controller_wrappers_and_tenant_login(monkeypatch):
    verify = MagicMock(return_value=True)
    token = MagicMock(return_value="jwt")
    tenant_login = MagicMock(return_value=SimpleNamespace(access_token="jwt-tenant"))
    super_login = MagicMock(return_value=SimpleNamespace(access_token="jwt-super"))
    validate = MagicMock(return_value={"valid": True})
    audit = MagicMock()
    decode = MagicMock(return_value={"tenant_id": 1, "session_id": "session-1"})
    monkeypatch.setattr(auth_controller, "verify_password_service", verify)
    monkeypatch.setattr(auth_controller, "create_access_token_service", token)
    monkeypatch.setattr(auth_controller, "login_user_service", tenant_login)
    monkeypatch.setattr(auth_controller, "login_super_user_service", super_login)
    monkeypatch.setattr(auth_controller, "validate_token_service", validate)
    monkeypatch.setattr(auth_controller, "create_login_session", audit)
    monkeypatch.setattr(auth_controller.jwt, "decode", decode)

    assert auth_controller.verify_password("a", "b") is True
    assert auth_controller.create_access_token({"sub": "1"}) == "jwt"
    datos = SimpleNamespace(
        username="user@example.com",
        password="pw",
        super_mode=False,
    )
    tenant_db = MagicMock()
    tenant_result = auth_controller.login_user(
        datos, tenant_db, client_ip="1.2.3.4"
    )
    assert tenant_result.access_token == "jwt-tenant"
    tenant_login.assert_called_once_with(
        datos,
        tenant_db,
        client_ip="1.2.3.4",
        user_agent=None,
    )

    super_datos = SimpleNamespace(
        username="super@example.com",
        password="pw",
        otp="123456",
        tenant="acme",
        super_mode=True,
    )
    super_db = MagicMock()
    super_result = auth_controller.login_user(
        super_datos, super_db, client_ip="1.2.3.4"
    )
    assert super_result.access_token == "jwt-super"
    assert super_login.call_count == 1
    assert auth_controller.login_super_user(
        SimpleNamespace(), MagicMock(), "1.2.3.4"
    ).access_token == "jwt-super"
    assert auth_controller.validate_token("jwt", MagicMock()) == {"valid": True}
    assert audit.call_count == 3


def test_auth_controller_current_user_falls_back_for_invalid_jwt(monkeypatch):
    fallback = MagicMock(return_value="tenant-user")
    monkeypatch.setattr(auth_controller, "get_current_user_from_token", fallback)
    monkeypatch.setattr(
        auth_controller.jwt,
        "decode",
        MagicMock(side_effect=JWTError("invalid")),
    )
    assert auth_controller.get_current_user("jwt", MagicMock()) == "tenant-user"
    fallback.assert_called_once()


def test_auth_controller_current_user_routes_super_and_tenant(monkeypatch):
    current = MagicMock(return_value="current")
    super_user = MagicMock(return_value="super-user")
    monkeypatch.setattr(auth_controller, "get_current_user_from_token", current)
    monkeypatch.setattr(auth_controller, "get_current_super_user", super_user)
    monkeypatch.setattr(
        auth_controller.jwt,
        "decode",
        MagicMock(return_value={"user_type": "SUPER"}),
    )
    assert auth_controller.get_current_user("jwt", MagicMock()) == "super-user"
    super_user.assert_called_once()

    auth_controller.jwt.decode.return_value = {"user_type": "TENANT"}
    assert auth_controller.get_current_user("jwt", MagicMock()) == "current"


def test_database_rls_and_db_dependencies(monkeypatch):
    db = MagicMock()
    database.set_rls_tenant(db, 7)
    db.execute.assert_called_once()
    assert db.execute.call_args.args[1] == {"tenant_id": "7"}

    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", MagicMock(return_value=session))
    generator = database.get_db()
    assert next(generator) is session
    with pytest.raises(StopIteration):
        next(generator)
    session.commit.assert_called_once()
    session.close.assert_called_once()


def test_database_db_dependency_rolls_back_and_reraises(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", MagicMock(return_value=session))
    generator = database.get_db()
    assert next(generator) is session
    error = RuntimeError("db error")
    with pytest.raises(RuntimeError, match="db error"):
        generator.throw(error)
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_database_bootstrap_dependency_success_and_error(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(
        database,
        "BootstrapSessionLocal",
        MagicMock(return_value=session),
    )
    generator = database.get_bootstrap_db()
    assert next(generator) is session
    with pytest.raises(StopIteration):
        next(generator)
    session.commit.assert_called_once()
    session.close.assert_called_once()

    session = MagicMock()
    monkeypatch.setattr(
        database,
        "BootstrapSessionLocal",
        MagicMock(return_value=session),
    )
    generator = database.get_bootstrap_db()
    next(generator)
    with pytest.raises(ValueError):
        generator.throw(ValueError("bootstrap error"))
    session.rollback.assert_called_once()
    session.close.assert_called_once()

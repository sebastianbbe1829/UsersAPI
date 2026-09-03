from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError

from UsersAPI.services import auth_context_service, user_notification_service


def test_user_notifications_activation_and_whatsapp(monkeypatch):
    send_email = MagicMock()
    send_whatsapp = MagicMock(return_value={"message_id": "1"})
    monkeypatch.setattr(user_notification_service, "send_email", send_email)
    monkeypatch.setattr(user_notification_service, "send_whatsapp", send_whatsapp)
    user = SimpleNamespace(name="Ana", dni="123")
    link = SimpleNamespace(email="ana@example.com", activation_token="abc", tenant_id=7, phone="300")

    user_notification_service.send_user_notifications(user, link, "Acme", "acme", False)
    assert send_email.call_args.kwargs["template"] == "activation"
    send_whatsapp.assert_called_once()

    send_email.reset_mock()
    send_whatsapp.reset_mock()
    user_notification_service.send_user_notifications(user, link, "Acme", "acme", True)
    assert send_email.call_args.kwargs["template"] == "reactivation"
    assert "reactivada" in send_email.call_args.kwargs["subject"]


def test_user_notifications_handles_email_failure_and_no_phone(monkeypatch):
    monkeypatch.setattr(user_notification_service, "send_email", MagicMock(side_effect=RuntimeError("mail")))
    whatsapp = MagicMock()
    monkeypatch.setattr(user_notification_service, "send_whatsapp", whatsapp)
    user = SimpleNamespace(name="Ana", dni="123")
    link = SimpleNamespace(email="ana@example.com", activation_token="abc", tenant_id=7, phone=None)
    user_notification_service.send_user_notifications(user, link, "Acme", "acme", False)
    whatsapp.assert_not_called()


def test_user_notifications_handles_whatsapp_failure_and_empty_response(monkeypatch):
    monkeypatch.setattr(user_notification_service, "send_email", MagicMock())
    whatsapp = MagicMock(side_effect=RuntimeError("wa"))
    monkeypatch.setattr(user_notification_service, "send_whatsapp", whatsapp)
    user = SimpleNamespace(name="Ana", dni="123")
    link = SimpleNamespace(email="ana@example.com", activation_token="abc", tenant_id=7, phone="300")
    user_notification_service.send_user_notifications(user, link, "Acme", "acme", False)
    whatsapp.assert_called_once()

    whatsapp.reset_mock(return_value=True, side_effect=True)
    whatsapp.return_value = None
    user_notification_service.send_user_notifications(user, link, "Acme", "acme", False)
    assert whatsapp.call_count == 2


def test_auth_context_service_error_branches(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(auth_context_service.jwt, "decode", MagicMock(side_effect=ExpiredSignatureError("expired")))
    with pytest.raises(HTTPException) as exc:
        auth_context_service.get_current_user_from_token("jwt", db)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expirado"

    monkeypatch.setattr(auth_context_service.jwt, "decode", MagicMock(side_effect=JWTError("bad")))
    with pytest.raises(HTTPException) as exc:
        auth_context_service.get_current_user_from_token("jwt", db)
    assert exc.value.status_code == 401

    monkeypatch.setattr(auth_context_service.jwt, "decode", MagicMock(return_value={}))
    with pytest.raises(HTTPException) as exc:
        auth_context_service.get_current_user_from_token("jwt", db)
    assert exc.value.detail == "No se pudo validar el token"

    monkeypatch.setattr(auth_context_service.jwt, "decode", MagicMock(return_value={"user_tenant_id": 8}))
    with pytest.raises(HTTPException) as exc:
        auth_context_service.get_current_user_from_token("jwt", db)
    assert exc.value.detail == "Token sin tenant asociado"


def test_auth_context_service_user_lookup_and_tenant_mismatch(monkeypatch):
    db = MagicMock()
    query = MagicMock()
    query.join.return_value = query
    query.filter.return_value = query
    db.query.return_value = query
    set_rls = MagicMock()
    monkeypatch.setattr(auth_context_service, "set_rls_tenant", set_rls)
    monkeypatch.setattr(auth_context_service.jwt, "decode", MagicMock(return_value={"user_tenant_id": 8, "tenant_id": 7}))

    query.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        auth_context_service.get_current_user_from_token("jwt", db)
    assert exc.value.detail == "Usuario no pertenece al tenant"
    set_rls.assert_called_once_with(db, 7)

    query.first.return_value = SimpleNamespace(tenant_id=9)
    with pytest.raises(HTTPException) as exc:
        auth_context_service.get_current_user_from_token("jwt", db)
    assert exc.value.detail == "El tenant del token no coincide con el usuario"

    valid = SimpleNamespace(tenant_id=7)
    query.first.return_value = valid
    assert auth_context_service.get_current_user_from_token("jwt", db) is valid

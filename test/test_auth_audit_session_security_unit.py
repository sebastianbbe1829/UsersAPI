from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt
from fastapi import HTTPException

from UsersAPI.models import AuthAuditDB, AuthSessionDB
from UsersAPI.services import auth_audit_service
from UsersAPI.services.auth_context_service import get_current_user_from_token
from UsersAPI.settings import settings


def _token(payload: dict) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def test_create_login_session_persists_session_and_login_audit():
    db = MagicMock()
    occurred_at = datetime(2026, 9, 3, 22, 40, 17)
    payload = {
        "tenant_id": 1,
        "user_tenant_id": 7,
        "user_type": "TENANT",
        "session_id": "session-1",
        "sub": "9999999999",
    }

    with patch.object(auth_audit_service, "set_rls_tenant") as set_rls, patch.object(
        auth_audit_service, "_now", return_value=occurred_at
    ):
        session = auth_audit_service.create_login_session(
            db,
            "token-1",
            payload,
            client_ip="127.0.0.1",
            user_agent="test-agent",
        )

    assert isinstance(session, AuthSessionDB)
    assert session.id == "session-1"
    assert session.tenant_id == 1
    assert session.user_tenant_id == 7
    assert session.session_kind == "TENANT"
    assert session.login_at == occurred_at
    assert session.status == "ACTIVE"
    assert session.token_hash == auth_audit_service._token_hash("token-1")
    set_rls.assert_called_once_with(db, 1)

    added = [call.args[0] for call in db.add.call_args_list]
    audit = next(item for item in added if isinstance(item, AuthAuditDB))
    assert audit.session_id == "session-1"
    assert audit.event_type == auth_audit_service.LOGIN_SUCCESS
    assert audit.actor_identifier == "9999999999"
    assert audit.client_ip == "127.0.0.1"
    assert audit.user_agent == "test-agent"
    assert audit.occurred_at == occurred_at


def test_create_login_session_generates_session_id_when_missing():
    db = MagicMock()
    payload = {"tenant_id": 2, "user_tenant_id": 8, "sub": "user-8"}

    with patch.object(auth_audit_service, "set_rls_tenant"), patch.object(
        auth_audit_service, "_now", return_value=datetime(2026, 9, 3, 22, 0, 0)
    ):
        session = auth_audit_service.create_login_session(db, "token-2", payload)

    assert session.id
    assert len(session.id) == 36


def test_close_login_session_closes_session_records_duration_and_logout_audit():
    db = MagicMock()
    login_at = datetime(2026, 9, 3, 22, 40, 0)
    logout_at = login_at + timedelta(seconds=35)
    payload = {
        "tenant_id": 1,
        "user_tenant_id": 7,
        "session_id": "session-3",
        "sub": "9999999999",
    }
    session = AuthSessionDB(
        id="session-3",
        tenant_id=1,
        user_tenant_id=7,
        session_kind="TENANT",
        token_hash=auth_audit_service._token_hash("token-3"),
        login_at=login_at,
        status="ACTIVE",
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = session
    db.query.return_value = query

    token = _token(payload)
    with patch.object(auth_audit_service, "set_rls_tenant"), patch.object(
        auth_audit_service, "_now", return_value=logout_at
    ):
        result = auth_audit_service.close_login_session(
            db,
            token,
            client_ip="10.0.0.5",
            user_agent="test-agent",
        )

    assert result is session
    assert session.logout_at == logout_at
    assert session.duration_seconds == 35
    assert session.status == "CLOSED"

    added = [call.args[0] for call in db.add.call_args_list]
    audit = next(item for item in added if isinstance(item, AuthAuditDB))
    assert audit.session_id == "session-3"
    assert audit.event_type == auth_audit_service.LOGOUT
    assert audit.actor_identifier == "9999999999"
    assert audit.occurred_at == logout_at
    assert audit.client_ip == "10.0.0.5"
    assert audit.user_agent == "test-agent"


def test_close_login_session_returns_none_for_invalid_token():
    db = MagicMock()

    result = auth_audit_service.close_login_session(db, "invalid-token")

    assert result is None
    db.query.assert_not_called()


def test_close_login_session_does_not_duplicate_audit_for_closed_session():
    db = MagicMock()
    session = AuthSessionDB(
        id="session-4",
        tenant_id=1,
        user_tenant_id=7,
        session_kind="TENANT",
        token_hash=auth_audit_service._token_hash("token-4"),
        login_at=datetime(2026, 9, 3, 22, 0, 0),
        status="CLOSED",
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = session
    db.query.return_value = query

    token = _token({"tenant_id": 1, "user_tenant_id": 7, "sub": "user-7"})
    result = auth_audit_service.close_login_session(db, token)

    assert result is session
    db.add.assert_not_called()


def test_auth_context_rejects_closed_or_missing_session():
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.first.return_value = None
    db.query.return_value = query
    token = _token(
        {
            "tenant_id": 1,
            "user_tenant_id": 7,
            "session_id": "closed-session",
            "sub": "9999999999",
        }
    )

    with patch("UsersAPI.services.auth_context_service.set_rls_tenant"):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "La sesión ya no es válida"

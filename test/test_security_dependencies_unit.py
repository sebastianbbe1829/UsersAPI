from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import JWTError

from UsersAPI.models import GlobalUserDB
from UsersAPI.security import dependencies


def make_db(tenant=None, user_tenant=None):
    tenant_query = MagicMock()
    tenant_query.filter.return_value.first.return_value = tenant
    user_tenant_query = MagicMock()
    user_tenant_query.filter.return_value.first.return_value = user_tenant

    db = MagicMock()
    db.query.side_effect = [tenant_query, user_tenant_query]
    return db


def make_super_user():
    return GlobalUserDB(
        email="super@example.com",
        password_hash="hash",
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        created_at=None,
        created_by="test",
    )


def test_get_current_tenant_requires_authenticated_user():
    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(None, "token", MagicMock())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Usuario no autenticado"


def test_get_current_tenant_rejects_inactive_user():
    user = SimpleNamespace(status=0)

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(user, "token", MagicMock())

    assert exc.value.status_code == 403
    assert exc.value.detail == "El usuario no está activo en el tenant"


def test_get_current_tenant_rejects_inactive_tenant():
    user = SimpleNamespace(status=1, tenant=SimpleNamespace(status=0))

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(user, "token", MagicMock())

    assert exc.value.status_code == 403
    assert exc.value.detail == "El tenant no está activo"


def test_get_current_tenant_sets_rls_for_normal_user(monkeypatch):
    user = SimpleNamespace(
        status=1,
        tenant=SimpleNamespace(status=1),
        tenant_id=42,
    )
    db = MagicMock()
    set_rls = MagicMock()
    monkeypatch.setattr(dependencies, "set_rls_tenant", set_rls)

    result = dependencies.get_current_tenant(user, "token", db)

    assert result is user
    set_rls.assert_called_once_with(db=db, tenant_id=42)


def test_get_current_tenant_rejects_invalid_super_token(monkeypatch):
    monkeypatch.setattr(
        dependencies.jwt,
        "decode",
        MagicMock(side_effect=JWTError("invalid")),
    )

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(make_super_user(), "token", MagicMock())

    assert exc.value.status_code == 401
    assert exc.value.detail == "No se pudo validar el contexto SUPER"


def test_get_current_tenant_rejects_non_super_token(monkeypatch):
    monkeypatch.setattr(
        dependencies.jwt,
        "decode",
        MagicMock(return_value={"user_type": "TENANT"}),
    )

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(make_super_user(), "token", MagicMock())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Contexto de autenticación inválido"


def test_get_current_tenant_rejects_super_token_without_tenant_context(monkeypatch):
    monkeypatch.setattr(
        dependencies.jwt,
        "decode",
        MagicMock(return_value={"user_type": "SUPER", "tenant_id": 1}),
    )

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(make_super_user(), "token", MagicMock())

    assert exc.value.status_code == 401
    assert exc.value.detail == "El token SUPER no contiene contexto de tenant"


def test_get_current_tenant_rejects_inactive_super_tenant(monkeypatch):
    monkeypatch.setattr(
        dependencies.jwt,
        "decode",
        MagicMock(
            return_value={
                "user_type": "SUPER",
                "tenant_id": 10,
                "tenant_slug": "demo",
            }
        ),
    )

    db = make_db(tenant=None)

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(make_super_user(), "token", db)

    assert exc.value.status_code == 403
    assert exc.value.detail == "El tenant no está activo"


def test_get_current_tenant_rejects_super_tenant_without_active_users(monkeypatch):
    monkeypatch.setattr(
        dependencies.jwt,
        "decode",
        MagicMock(
            return_value={
                "user_type": "SUPER",
                "tenant_id": 10,
                "tenant_slug": "demo",
            }
        ),
    )
    tenant = SimpleNamespace(id=10)
    db = make_db(tenant=tenant, user_tenant=None)

    with pytest.raises(HTTPException) as exc:
        dependencies.get_current_tenant(make_super_user(), "token", db)

    assert exc.value.status_code == 403
    assert exc.value.detail == "El tenant no tiene usuarios activos"


def test_get_current_tenant_sets_rls_for_super_context(monkeypatch):
    monkeypatch.setattr(
        dependencies.jwt,
        "decode",
        MagicMock(
            return_value={
                "user_type": "SUPER",
                "tenant_id": 10,
                "tenant_slug": "demo",
            }
        ),
    )
    tenant = SimpleNamespace(id=10)
    user_tenant = SimpleNamespace(tenant_id=10, status=1)
    db = make_db(tenant=tenant, user_tenant=user_tenant)
    set_rls = MagicMock()
    monkeypatch.setattr(dependencies, "set_rls_tenant", set_rls)

    result = dependencies.get_current_tenant(make_super_user(), "token", db)

    assert result is user_tenant
    set_rls.assert_called_once_with(db=db, tenant_id=10)

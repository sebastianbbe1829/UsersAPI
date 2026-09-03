from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from UsersAPI.services import token_validation_service as service


def _db(user_tenant):
    query = MagicMock()
    query.join.return_value = query
    query.filter.return_value = query
    query.first.return_value = user_tenant
    db = MagicMock()
    db.query.return_value = query
    return db


def _token(**claims):
    return jwt.encode(claims, service.SECRET_KEY, algorithm=service.ALGORITHM)


def test_validate_token_success(monkeypatch):
    tenant = SimpleNamespace(id=5, slug="acme")
    user = SimpleNamespace(dni="123")
    relation = SimpleNamespace(
        id=9,
        tenant_id=5,
        email="a@b.com",
        user=user,
        tenant=tenant,
    )
    db = _db(relation)
    monkeypatch.setattr(service, "set_rls_tenant", MagicMock())
    token = _token(user_tenant_id=9, tenant_id=5, exp=4102444800)

    result = service.validate_token(token, db)

    assert result["valid"] is True
    assert result["user_tenant_id"] == 9
    assert result["user"]["email"] == "a@b.com"
    assert result["tenant"]["slug"] == "acme"
    service.set_rls_tenant.assert_called_once_with(db, 5)


def test_validate_token_without_user_tenant():
    db = MagicMock()
    token = _token(tenant_id=5)
    with pytest.raises(HTTPException) as exc:
        service.validate_token(token, db)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Token inválido"


def test_validate_token_without_tenant():
    db = MagicMock()
    token = _token(user_tenant_id=9)
    with pytest.raises(HTTPException) as exc:
        service.validate_token(token, db)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Token sin tenant asociado"


def test_validate_token_user_not_found(monkeypatch):
    db = _db(None)
    monkeypatch.setattr(service, "set_rls_tenant", MagicMock())
    token = _token(user_tenant_id=9, tenant_id=5)
    with pytest.raises(HTTPException) as exc:
        service.validate_token(token, db)
    assert exc.value.status_code == 404


def test_validate_token_tenant_mismatch(monkeypatch):
    relation = SimpleNamespace(id=9, tenant_id=7)
    db = _db(relation)
    monkeypatch.setattr(service, "set_rls_tenant", MagicMock())
    token = _token(user_tenant_id=9, tenant_id=5)
    with pytest.raises(HTTPException) as exc:
        service.validate_token(token, db)
    assert exc.value.status_code == 401
    assert "no coincide" in exc.value.detail


def test_validate_token_without_exp(monkeypatch):
    tenant = SimpleNamespace(id=5, slug="acme")
    user = SimpleNamespace(dni="123")
    relation = SimpleNamespace(
        id=9,
        tenant_id=5,
        email="a@b.com",
        user=user,
        tenant=tenant,
    )
    db = _db(relation)
    monkeypatch.setattr(service, "set_rls_tenant", MagicMock())
    token = _token(user_tenant_id=9, tenant_id=5)
    result = service.validate_token(token, db)
    assert result["expiration"] is None
    assert result["remaining_seconds"] is None
    assert result["remaining_minutes_rounded"] is None


def test_validate_token_invalid_jwt():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        service.validate_token("not-a-jwt", db)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Token inválido"

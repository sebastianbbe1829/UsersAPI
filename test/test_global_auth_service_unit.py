from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from UsersAPI.services import global_auth_service as service


def _db(query_result=None, scalar=None):
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = query_result
    db = MagicMock()
    db.query.return_value = query
    db.execute.return_value.scalar.return_value = scalar
    return db, query


def test_fernet_fallback_and_invalid_key(monkeypatch):
    monkeypatch.setattr(service, "settings", replace(service.settings, super_mfa_encryption_key=""))
    assert service._fernet()
    monkeypatch.setattr(service, "settings", replace(service.settings, super_mfa_encryption_key="bad"))
    with pytest.raises(RuntimeError):
        service._fernet()


def test_decrypt_invalid_token():
    with pytest.raises(HTTPException) as exc:
        service._decrypt_mfa_secret("not-valid")
    assert exc.value.status_code == 500


def test_validate_bootstrap_secret(monkeypatch):
    monkeypatch.setattr(service, "settings", replace(service.settings, super_bootstrap_secret="secret"))
    service._validate_bootstrap_secret("secret")
    with pytest.raises(HTTPException) as exc:
        service._validate_bootstrap_secret("bad")
    assert exc.value.status_code == 401
    monkeypatch.setattr(service, "settings", replace(service.settings, super_bootstrap_secret=""))
    with pytest.raises(HTTPException) as exc:
        service._validate_bootstrap_secret("secret")
    assert exc.value.status_code == 503


def test_bootstrap_existing_super_and_duplicate_email(monkeypatch):
    monkeypatch.setattr(service, "settings", replace(service.settings, super_bootstrap_secret="secret"))
    existing = SimpleNamespace(id=1)
    db, _ = _db(existing)
    with pytest.raises(HTTPException) as exc:
        service.bootstrap_super_user(SimpleNamespace(email="x", password="p"), "secret", db)
    assert exc.value.status_code == 409
    db, query = _db(None)
    query.first.side_effect = [None, SimpleNamespace(id=2)]
    with pytest.raises(HTTPException) as exc:
        service.bootstrap_super_user(SimpleNamespace(email=" X@TEST ", password="p"), "secret", db)
    assert exc.value.status_code == 409


def test_bootstrap_success(monkeypatch):
    monkeypatch.setattr(service, "settings", replace(service.settings, super_bootstrap_secret="secret"))
    db, query = _db(None)
    query.first.return_value = None
    user = SimpleNamespace(id=7, email="x@test.com")
    monkeypatch.setattr(service, "GlobalUserDB", MagicMock(return_value=user))
    monkeypatch.setattr(service, "get_password_hash", lambda _: "hash")
    monkeypatch.setattr(service.pyotp, "random_base32", lambda: "SECRET")
    result = service.bootstrap_super_user(SimpleNamespace(email=" X@TEST.COM ", password="p"), "secret", db)
    assert result.id == 7
    assert result.email == "x@test.com"
    db.add.assert_called_once_with(user)
    db.flush.assert_called_once()


def test_verify_bootstrap_mfa_branches(monkeypatch):
    monkeypatch.setattr(service, "settings", replace(service.settings, super_bootstrap_secret="secret"))
    db, query = _db(None)
    data = SimpleNamespace(user_id=1, otp="123")
    with pytest.raises(HTTPException) as exc:
        service.verify_bootstrap_mfa(data, "secret", db)
    assert exc.value.status_code == 404
    user = SimpleNamespace(id=1, mfa_verified_at=object())
    db, query = _db(user)
    with pytest.raises(HTTPException) as exc:
        service.verify_bootstrap_mfa(data, "secret", db)
    assert exc.value.status_code == 409
    user = SimpleNamespace(id=1, mfa_verified_at=None, mfa_enabled=False, mfa_secret_encrypted=None)
    db, query = _db(user)
    with pytest.raises(HTTPException) as exc:
        service.verify_bootstrap_mfa(data, "secret", db)
    assert exc.value.status_code == 409
    user = SimpleNamespace(id=1, mfa_verified_at=None, mfa_enabled=True, mfa_secret_encrypted="enc", email="x@test.com")
    db, query = _db(user)
    monkeypatch.setattr(service, "_decrypt_mfa_secret", lambda _: "SECRET")
    monkeypatch.setattr(service.pyotp.TOTP, "verify", lambda self, otp, valid_window: False)
    with pytest.raises(HTTPException) as exc:
        service.verify_bootstrap_mfa(data, "secret", db)
    assert exc.value.status_code == 401
    monkeypatch.setattr(service.pyotp.TOTP, "verify", lambda self, otp, valid_window: True)
    result = service.verify_bootstrap_mfa(data, "secret", db)
    assert result.id == 1
    assert result.email == "x@test.com"
    assert result.mfa_verified is True


def test_login_super_tenant_and_credentials_branches(monkeypatch):
    data = SimpleNamespace(email=" X@TEST.COM ", tenant=" ACME ", password="bad", otp=None)
    db, query = _db(None, None)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 404
    tenant = SimpleNamespace(id=5, slug="acme")
    db, query = _db(tenant, None)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    user = SimpleNamespace(id=1, email="x@test.com", is_active=False, is_superuser=True, password_hash="hash", mfa_enabled=False)
    db, query = _db(tenant, user)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    user.is_active = True
    monkeypatch.setattr(service, "verify_password", lambda *_: False)
    db, query = _db(tenant, user)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401


def test_login_super_mfa_branches(monkeypatch):
    tenant = SimpleNamespace(id=5, slug="acme")
    user = SimpleNamespace(id=1, email="x@test.com", is_active=True, is_superuser=True, password_hash="hash", mfa_enabled=True, mfa_verified_at=None, mfa_secret_encrypted=None)
    data = SimpleNamespace(email="x", tenant="acme", password="p", otp=None)
    monkeypatch.setattr(service, "verify_password", lambda *_: True)
    db, query = _db(tenant, user)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 403
    user.mfa_verified_at = object()
    db, query = _db(tenant, user)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    data.otp = "123"
    db, query = _db(tenant, user)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 500
    user.mfa_secret_encrypted = "enc"
    monkeypatch.setattr(service, "_decrypt_mfa_secret", lambda _: "SECRET")
    monkeypatch.setattr(service.pyotp.TOTP, "verify", lambda *args, **kwargs: False)
    db, query = _db(tenant, user)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    monkeypatch.setattr(service.pyotp.TOTP, "verify", lambda *args, **kwargs: True)
    monkeypatch.setattr(service, "_create_super_token", lambda *_: "token")
    db, query = _db(tenant, user)
    result = service.login_super_user(data, db, "1.2.3.4")
    assert result.access_token == "token"
    assert user.last_login_ip == "1.2.3.4"


def test_get_current_super_user_token_branches(monkeypatch):
    db, query = _db()
    with pytest.raises(HTTPException):
        service.get_current_super_user("bad", db)
    token = jwt.encode({"user_type": "TENANT"}, service.settings.secret_key, algorithm=service.settings.algorithm)
    with pytest.raises(HTTPException):
        service.get_current_super_user(token, db)
    token = jwt.encode({"user_type": "SUPER"}, service.settings.secret_key, algorithm=service.settings.algorithm)
    with pytest.raises(HTTPException):
        service.get_current_super_user(token, db)


def test_get_current_super_user_session_and_tenant_validation(monkeypatch):
    user = SimpleNamespace(session_id="session")
    token = jwt.encode({"user_type": "SUPER", "global_user_id": 1, "session_id": "other", "tenant_id": 5, "tenant_slug": "acme"}, service.settings.secret_key, algorithm=service.settings.algorithm)
    db, query = _db(None, 5)
    with pytest.raises(HTTPException) as exc:
        service.get_current_super_user(token, db)
    assert exc.value.status_code == 401
    token = jwt.encode({"user_type": "SUPER", "global_user_id": 1, "session_id": "session", "tenant_id": 5, "tenant_slug": "acme"}, service.settings.secret_key, algorithm=service.settings.algorithm)
    db, query = _db(user, None)
    with pytest.raises(HTTPException) as exc:
        service.get_current_super_user(token, db)
    assert exc.value.status_code == 401
    db, query = _db(user, 6)
    with pytest.raises(HTTPException) as exc:
        service.get_current_super_user(token, db)
    assert exc.value.status_code == 401
    db, query = _db(user, 5)
    monkeypatch.setattr(service, "set_rls_tenant", MagicMock())
    assert service.get_current_super_user(token, db) is user

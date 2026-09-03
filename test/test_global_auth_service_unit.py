from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.services import global_auth_service as service


def _db(query_result=None, scalar=None):
    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = query_result
    db = MagicMock()
    db.query.return_value = query
    db.execute.return_value.scalar.return_value = scalar
    return db, query


def test_fernet_branches(monkeypatch):
    monkeypatch.setenv("FERNET_KEY", "invalid")
    assert service._get_fernet() is None
    monkeypatch.delenv("FERNET_KEY", raising=False)
    assert service._get_fernet() is None


def test_decrypt_invalid_token(monkeypatch):
    monkeypatch.setattr(service, "_get_fernet", lambda: None)
    assert service._decrypt_mfa_secret("bad") is None


def test_validate_bootstrap_secret_branches(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_SECRET", "secret")
    assert service._validate_bootstrap_secret("secret") is True
    assert service._validate_bootstrap_secret("bad") is False
    monkeypatch.delenv("BOOTSTRAP_SECRET", raising=False)
    assert service._validate_bootstrap_secret("secret") is False


def test_bootstrap_super_existing_and_duplicate(monkeypatch):
    data = SimpleNamespace(email=" X@TEST.COM ", password="p", mfa_secret="m")
    db, query = _db(SimpleNamespace(id=1))
    monkeypatch.setattr(service, "_validate_bootstrap_secret", lambda *_: True)
    with pytest.raises(HTTPException) as exc:
        service.bootstrap_super_user(data, "secret", db)
    assert exc.value.status_code == 409
    db, query = _db(None)
    query.first.return_value = SimpleNamespace(id=2)
    with pytest.raises(HTTPException) as exc:
        service.bootstrap_super_user(data, "secret", db)
    assert exc.value.status_code == 409


def test_bootstrap_super_success(monkeypatch):
    data = SimpleNamespace(email=" X@TEST.COM ", password="p", mfa_secret="m")
    db, query = _db(None)
    monkeypatch.setattr(service, "_validate_bootstrap_secret", lambda *_: True)
    monkeypatch.setattr(service, "hash_password", lambda *_: "hash")
    monkeypatch.setattr(service, "_encrypt_mfa_secret", lambda *_: "enc")
    monkeypatch.setattr(service, "generate_mfa_secret", lambda: "secret")
    result = service.bootstrap_super_user(data, "secret", db)
    assert result.email == "x@test.com"
    assert result.mfa_enabled is True
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_verify_bootstrap_mfa_branches(monkeypatch):
    data = SimpleNamespace(email="x", otp="123")
    user = SimpleNamespace(
        id=1,
        email="x@test.com",
        is_active=True,
        is_superuser=True,
        mfa_enabled=True,
        mfa_secret_encrypted="enc",
        mfa_verified_at=None,
    )
    db, query = _db(user)
    monkeypatch.setattr(service, "_decrypt_mfa_secret", lambda _: "secret")
    monkeypatch.setattr(service.pyotp.TOTP, "verify", lambda *args, **kwargs: True)
    result = service.verify_bootstrap_mfa(data, "secret", db)
    assert result.id == 1
    assert result.email == "x@test.com"
    assert result.mfa_verified is True


def test_login_super_tenant_and_credentials_branches(monkeypatch):
    data = SimpleNamespace(
        email=" X@TEST.COM ", tenant=" ACME ", password="bad", otp=None
    )
    db, query = _db(None, None)
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 404
    tenant = SimpleNamespace(id=5, slug="acme")
    user = SimpleNamespace(
        id=1,
        email="x@test.com",
        is_active=False,
        is_superuser=True,
        password_hash="hash",
        mfa_enabled=False,
    )
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    user.is_active = True
    monkeypatch.setattr(service, "verify_password", lambda *_: False)
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401


def test_login_super_mfa_branches(monkeypatch):
    tenant = SimpleNamespace(id=5, slug="acme")
    user = SimpleNamespace(
        id=1,
        email="x@test.com",
        is_active=True,
        is_superuser=True,
        password_hash="hash",
        mfa_enabled=True,
        mfa_verified_at=None,
        mfa_secret_encrypted=None,
    )
    data = SimpleNamespace(email="x", tenant="acme", password="p", otp=None)
    monkeypatch.setattr(service, "verify_password", lambda *_: True)
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 403
    user.mfa_verified_at = object()
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    data.otp = "123"
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 500
    user.mfa_secret_encrypted = "enc"
    monkeypatch.setattr(service, "_decrypt_mfa_secret", lambda _: "SECRET")
    monkeypatch.setattr(
        service.pyotp.TOTP, "verify", lambda *args, **kwargs: False
    )
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    with pytest.raises(HTTPException) as exc:
        service.login_super_user(data, db)
    assert exc.value.status_code == 401
    monkeypatch.setattr(
        service.pyotp.TOTP, "verify", lambda *args, **kwargs: True
    )
    monkeypatch.setattr(service, "_create_super_token", lambda *_: "token")
    db, query = _db(None, 5)
    query.first.side_effect = [tenant, user]
    result = service.login_super_user(data, db, "1.2.3.4")
    assert result.access_token == "token"
    assert user.last_login_ip == "1.2.3.4"


def test_get_current_super_user_token_branches(monkeypatch):
    db, query = _db()
    with pytest.raises(HTTPException) as exc:
        service.get_current_super_user("bad", db)
    assert exc.value.status_code == 401

    monkeypatch.setattr(service, "decode_token", lambda *_: {})
    with pytest.raises(HTTPException) as exc:
        service.get_current_super_user("token", db)
    assert exc.value.status_code == 401


def test_get_current_super_session_and_tenant_validation(monkeypatch):
    payload = {"sub": "1", "tenant_id": 5, "tenant_slug": "acme"}
    monkeypatch.setattr(service, "decode_token", lambda *_: payload)
    user = SimpleNamespace(id=1, email="x@test.com", is_active=True, is_superuser=True)
    tenant = SimpleNamespace(id=5, slug="acme", status=1)
    db, query = _db(user)
    query.first.side_effect = [tenant, user]
    result = service.get_current_super_user("token", db)
    assert result.id == 1

    db, query = _db(None)
    with pytest.raises(HTTPException) as exc:
        service.get_current_super_user("token", db)
    assert exc.value.status_code in (401, 403)

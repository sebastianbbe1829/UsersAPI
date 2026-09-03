from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.services import super_mfa_service as service


def _user(**overrides):
    values = {
        "is_active": True,
        "is_superuser": True,
        "mfa_enabled": True,
        "mfa_verified_at": object(),
        "mfa_secret_encrypted": "encrypted-secret",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "user",
    [_user(is_active=False), _user(is_superuser=False)],
)
def test_verify_super_mfa_rejects_non_super(user):
    with pytest.raises(HTTPException) as exc:
        service.verify_super_mfa_otp(user, "123456")
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "user",
    [_user(mfa_enabled=False), _user(mfa_verified_at=None)],
)
def test_verify_super_mfa_requires_verified_mfa(user):
    with pytest.raises(HTTPException) as exc:
        service.verify_super_mfa_otp(user, "123456")
    assert exc.value.status_code == 403


def test_verify_super_mfa_requires_secret():
    with pytest.raises(HTTPException) as exc:
        service.verify_super_mfa_otp(_user(mfa_secret_encrypted=None), "123456")
    assert exc.value.status_code == 500


def test_verify_super_mfa_success(monkeypatch):
    decrypt = MagicMock(return_value="SECRET")
    totp = MagicMock()
    totp.verify.return_value = True
    monkeypatch.setattr(service, "_decrypt_mfa_secret", decrypt)
    monkeypatch.setattr(service.pyotp, "TOTP", MagicMock(return_value=totp))

    assert service.verify_super_mfa_otp(_user(), "123456") is None
    decrypt.assert_called_once_with("encrypted-secret")
    totp.verify.assert_called_once_with("123456", valid_window=1)


def test_verify_super_mfa_invalid_code(monkeypatch):
    monkeypatch.setattr(service, "_decrypt_mfa_secret", lambda _: "SECRET")
    totp = MagicMock()
    totp.verify.return_value = False
    monkeypatch.setattr(service.pyotp, "TOTP", MagicMock(return_value=totp))

    with pytest.raises(HTTPException) as exc:
        service.verify_super_mfa_otp(_user(), "000000")
    assert exc.value.status_code == 401

from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from UsersAPI.controllers import otp_controller as controller
from UsersAPI.schemas.otp import OTPGenerateRequest, OTPValidateRequest
from UsersAPI.settings import settings


def test_validate_otp_api_key(monkeypatch):
    monkeypatch.setattr(
        controller,
        "settings",
        replace(settings, otp_api_key="secret"),
    )
    controller.validate_otp_api_key("secret")
    with pytest.raises(HTTPException) as exc:
        controller.validate_otp_api_key("bad")
    assert exc.value.status_code == 403
    monkeypatch.setattr(
        controller,
        "settings",
        replace(settings, otp_api_key=""),
    )
    with pytest.raises(HTTPException) as exc:
        controller.validate_otp_api_key("secret")
    assert exc.value.status_code == 500


def test_create_otp_success_and_value_error(monkeypatch):
    expires = datetime.now(timezone.utc)
    monkeypatch.setattr(controller, "generate_otp", lambda *args, **kwargs: expires)
    data = OTPGenerateRequest(destination="3001234567", purpose="activation")
    result = controller.create_otp(data, MagicMock())
    assert result.expires_at == expires

    def fail(*args, **kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(controller, "generate_otp", fail)
    with pytest.raises(HTTPException) as exc:
        controller.create_otp(data, MagicMock())
    assert exc.value.status_code == 400
    assert exc.value.detail == "bad"


def test_create_otp_unexpected_error(monkeypatch):
    monkeypatch.setattr(
        controller,
        "generate_otp",
        MagicMock(side_effect=RuntimeError("down")),
    )
    data = OTPGenerateRequest(destination="3001234567", purpose="activation")
    with pytest.raises(HTTPException) as exc:
        controller.create_otp(data, MagicMock())
    assert exc.value.status_code == 502


def test_verify_otp_valid_and_invalid(monkeypatch):
    data = OTPValidateRequest(destination="3001234567", purpose="activation", code="123456")
    monkeypatch.setattr(controller, "validate_otp", lambda *args, **kwargs: True)
    result = controller.verify_otp(data, MagicMock())
    assert result.valid is True
    assert "válido" in result.message
    monkeypatch.setattr(controller, "validate_otp", lambda *args, **kwargs: False)
    result = controller.verify_otp(data, MagicMock())
    assert result.valid is False
    assert "inválido" in result.message

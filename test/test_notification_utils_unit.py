from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from UsersAPI.util import email_utils, whatsapp_utils


def test_format_number_variants():
    assert whatsapp_utils.format_number("+573001234567") == "573001234567"
    assert whatsapp_utils.format_number("573001234567") == "573001234567"
    assert whatsapp_utils.format_number("3001234567") == "573001234567"


@pytest.mark.parametrize("field", ["WHATSAPP_API_URL", "ACCESS_TOKEN", "WHATSAPP_PHONE_ID"])
def test_send_whatsapp_missing_configuration(monkeypatch, field):
    for name in ("WHATSAPP_API_URL", "ACCESS_TOKEN", "WHATSAPP_PHONE_ID"):
        monkeypatch.setattr(whatsapp_utils, name, "ok")
    monkeypatch.setattr(whatsapp_utils, field, "")
    assert whatsapp_utils.send_whatsapp("3001234567", "hola") is None


def test_send_whatsapp_missing_number_and_text(monkeypatch):
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_API_URL", "https://x/")
    monkeypatch.setattr(whatsapp_utils, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_PHONE_ID", "123")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_MODE", "text")
    assert whatsapp_utils.send_whatsapp("") is None
    assert whatsapp_utils.send_whatsapp("3001234567") is None


def test_send_whatsapp_text_success_and_json_error(monkeypatch):
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_API_URL", "https://x/")
    monkeypatch.setattr(whatsapp_utils, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_PHONE_ID", "123")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_MODE", "text")
    response = MagicMock(ok=True, status_code=200, text="ok")
    response.json.side_effect = ValueError()
    post = MagicMock(return_value=response)
    monkeypatch.setattr(whatsapp_utils.requests, "post", post)
    result = whatsapp_utils.send_whatsapp("3001234567", "hola")
    assert result == {"status_code": 200, "text": "ok"}
    assert post.call_args.kwargs["json"]["type"] == "text"


def test_send_whatsapp_template_success_with_parameters(monkeypatch):
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_API_URL", "https://x/")
    monkeypatch.setattr(whatsapp_utils, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_PHONE_ID", "123")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_MODE", "template")
    response = MagicMock(ok=True, status_code=200)
    response.json.return_value = {"messages": [{"id": "1"}]}
    post = MagicMock(return_value=response)
    monkeypatch.setattr(whatsapp_utils.requests, "post", post)
    result = whatsapp_utils.send_whatsapp("+573001234567", template_name="otp", parameters=[123, "abc"])
    assert result["messages"][0]["id"] == "1"
    payload = post.call_args.kwargs["json"]
    assert payload["template"]["components"][0]["parameters"][0]["text"] == "123"


def test_send_whatsapp_http_and_request_errors(monkeypatch):
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_API_URL", "https://x/")
    monkeypatch.setattr(whatsapp_utils, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_PHONE_ID", "123")
    monkeypatch.setattr(whatsapp_utils, "WHATSAPP_MODE", "template")
    bad = MagicMock(ok=False, status_code=400, text="bad")
    monkeypatch.setattr(whatsapp_utils.requests, "post", MagicMock(return_value=bad))
    assert whatsapp_utils.send_whatsapp("3001234567") is None
    monkeypatch.setattr(
        whatsapp_utils.requests,
        "post",
        MagicMock(side_effect=requests.exceptions.RequestException("down")),
    )
    assert whatsapp_utils.send_whatsapp("3001234567") is None


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


def test_send_email_validation(monkeypatch):
    _configure_email(monkeypatch)
    with pytest.raises(ValueError):
        email_utils.send_email("a@b", "s", "m", template="bad")
    monkeypatch.setattr(email_utils, "BREVO_API_KEY", "")
    with pytest.raises(RuntimeError):
        email_utils.send_email("a@b", "s", "m")


def test_send_email_default_success_and_attachment(monkeypatch):
    template = _configure_email(monkeypatch)
    response = MagicMock(status_code=201)
    response.json.return_value = {"messageId": "abc"}
    post = MagicMock(return_value=response)
    monkeypatch.setattr(email_utils.requests, "post", post)
    result = email_utils.send_email(
        "a@b", "s", "m", attachments=[{"name": "x", "content": "Y"}]
    )
    assert result == {"status": "sent", "message_id": "abc"}
    assert post.call_args.kwargs["json"]["attachment"]
    template.render.assert_called_once()


def test_send_email_activation_and_updated_paths(monkeypatch):
    _configure_email(monkeypatch)
    response = MagicMock(status_code=201)
    response.json.return_value = {"messageId": "id"}
    monkeypatch.setattr(email_utils.requests, "post", MagicMock(return_value=response))
    email_utils.send_email(
        "a@b", "UsersAPI activation", "m", dni="1", token="t", tenant_slug="acme",
        tenant_name=" Acme ", template="activation"
    )
    email_utils.send_email(
        "a@b", "UsersAPI updated", "m", tenant_slug="acme", template="updated"
    )


def test_send_email_configuration_and_http_errors(monkeypatch):
    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils, "FRONTEND_URL", "")
    with pytest.raises(RuntimeError, match="FRONTEND_URL"):
        email_utils.send_email("a@b", "s", "m", template="updated", tenant_slug="x")
    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils.os.path, "isfile", lambda _: False)
    with pytest.raises(RuntimeError, match="template not found"):
        email_utils.send_email("a@b", "s", "m")
    _configure_email(monkeypatch)
    monkeypatch.setattr(email_utils.requests, "post", MagicMock(side_effect=requests.exceptions.Timeout()))
    with pytest.raises(RuntimeError, match="Timeout"):
        email_utils.send_email("a@b", "s", "m")

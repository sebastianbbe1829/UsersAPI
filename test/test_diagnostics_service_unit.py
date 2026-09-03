from types import SimpleNamespace
from unittest.mock import MagicMock

from UsersAPI.services import diagnostics_service as service


def test_get_client_ip_diagnostic_with_client():
    request = SimpleNamespace(client=SimpleNamespace(host="10.0.0.15"))
    result = service.get_client_ip_diagnostic(request)
    assert result == {"status": "enabled", "client_host": "10.0.0.15"}


def test_get_client_ip_diagnostic_without_client():
    request = SimpleNamespace(client=None)
    result = service.get_client_ip_diagnostic(request)
    assert result == {"status": "enabled", "client_host": "unknown"}


def test_get_client_ip_diagnostic_logs_client_host(monkeypatch):
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    logger = MagicMock()
    monkeypatch.setattr(service, "logger", logger)

    result = service.get_client_ip_diagnostic(request)

    assert result["client_host"] == "127.0.0.1"
    logger.warning.assert_called_once_with(
        "Rate limiter IP diagnostic requested: client_host=%s",
        "127.0.0.1",
    )

from fastapi import Request
from fastapi.exceptions import HTTPException

from UsersAPI.security.rate_limiter import InMemoryRateLimiter


def make_request(client_host: str | None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
        "client": (client_host, 12345) if client_host is not None else None,
    }
    return Request(scope)


def test_rate_limiter_allows_attempts_up_to_limit():
    limiter = InMemoryRateLimiter()

    limiter.check("login:test", 2, 60)
    limiter.check("login:test", 2, 60)


def test_rate_limiter_blocks_attempt_after_limit():
    limiter = InMemoryRateLimiter()

    limiter.check("login:test", 1, 60)

    try:
        limiter.check("login:test", 1, 60)
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.headers["Retry-After"]
        assert exc.detail == "Demasiados intentos. Inténtalo nuevamente más tarde."
    else:
        raise AssertionError("Expected HTTP 429")


def test_rate_limiter_keeps_keys_isolated():
    limiter = InMemoryRateLimiter()

    limiter.check("login:user-a", 1, 60)
    limiter.check("login:user-b", 1, 60)


def test_client_ip_uses_request_client_host_without_trusting_forwarded_headers():
    limiter = InMemoryRateLimiter()
    request = make_request("10.0.0.25")
    request.scope["headers"] = [
        (b"x-forwarded-for", b"203.0.113.10"),
        (b"x-real-ip", b"203.0.113.11"),
    ]

    assert limiter.client_ip(request) == "10.0.0.25"


def test_client_ip_returns_unknown_when_client_is_unavailable():
    limiter = InMemoryRateLimiter()
    request = make_request(None)

    assert limiter.client_ip(request) == "unknown"


def test_in_memory_rate_limiter_ping_and_status():
    limiter = InMemoryRateLimiter()
    assert limiter.ping() is True
    assert limiter.status() == {"backend": "memory", "connected": True}


def test_redis_rate_limiter_ping_and_status(monkeypatch):
    from unittest.mock import MagicMock
    import redis
    from UsersAPI.security.rate_limiter import RedisRateLimiter

    mock_client = MagicMock()
    mock_client.ping.return_value = True
    monkeypatch.setattr(redis.Redis, "from_url", lambda *args, **kwargs: mock_client)

    limiter = RedisRateLimiter("redis://localhost:6379/0")
    assert limiter.ping() is True
    assert limiter.status() == {"backend": "redis", "connected": True}

    mock_client.ping.side_effect = redis.exceptions.ConnectionError("Failed")
    assert limiter.ping() is False
    assert limiter.status() == {"backend": "redis", "connected": False}


def test_health_endpoint_reports_rate_limiter_status():
    from fastapi.testclient import TestClient
    from UsersAPI.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "rate_limiter" in data
    assert "backend" in data["rate_limiter"]
    assert "connected" in data["rate_limiter"]

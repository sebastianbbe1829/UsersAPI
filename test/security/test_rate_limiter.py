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

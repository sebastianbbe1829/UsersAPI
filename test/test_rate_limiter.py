import pytest
from fastapi import HTTPException

from UsersAPI.security.rate_limiter import InMemoryRateLimiter


def test_rate_limiter_allows_requests_under_limit():
    limiter = InMemoryRateLimiter()

    for _ in range(3):
        limiter.check("test:key", limit=3, window_seconds=60)


def test_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()

    for _ in range(2):
        limiter.check("test:key", limit=2, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        limiter.check("test:key", limit=2, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_rate_limiter_uses_independent_keys():
    limiter = InMemoryRateLimiter()

    limiter.check("tenant-a:user-a", limit=1, window_seconds=60)
    limiter.check("tenant-b:user-a", limit=1, window_seconds=60)


def test_rate_limiter_normalizes_identifiers():
    limiter = InMemoryRateLimiter()

    assert limiter.normalize("  USER@Example.COM ") == "user@example.com"
    assert limiter.normalize(None) == ""

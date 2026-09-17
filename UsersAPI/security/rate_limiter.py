from collections import defaultdict, deque
from threading import Lock
from time import monotonic, time
from uuid import uuid4

from fastapi import HTTPException, Request, status

from ..logging_config import logger
from ..settings import APP_ENV, settings

MAX_WINDOW_SECONDS = 15 * 60
CLEANUP_INTERVAL_SECONDS = 60


class InMemoryRateLimiter:
    """Rate limiter sencillo para una única instancia de la API.

    Mantiene ventanas deslizantes en memoria. Si la aplicación escala a varias
    instancias, este componente debe migrarse a un almacenamiento compartido
    como Redis.
    """

    def __init__(self):
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._last_cleanup = 0.0

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return

        cutoff = now - MAX_WINDOW_SECONDS
        stale_keys = [
            key
            for key, attempts in self._attempts.items()
            if not attempts or attempts[-1] <= cutoff
        ]
        for key in stale_keys:
            self._attempts.pop(key, None)

        self._last_cleanup = now

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            self._cleanup(now)
            attempts = self._attempts[key]

            while attempts and attempts[0] <= window_start:
                attempts.popleft()

            if len(attempts) >= limit:
                retry_after = max(1, int(attempts[0] + window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiados intentos. Inténtalo nuevamente más tarde.",
                    headers={"Retry-After": str(retry_after)},
                )

            attempts.append(now)

    def reset(self) -> None:
        """Limpia el estado del limiter; usado para aislar pruebas."""
        with self._lock:
            self._attempts.clear()
            self._last_cleanup = 0.0

    def ping(self) -> bool:
        return True

    def status(self) -> dict[str, object]:
        return {"backend": "memory", "connected": True}

    @staticmethod
    def client_ip(request: Request) -> str:
        """Obtiene el identificador de cliente disponible para FastAPI.

        No confía ciegamente en X-Forwarded-For/X-Real-IP, porque esos headers
        pueden ser enviados por el cliente cuando no existe una capa proxy
        confiable configurada delante del backend.
        """
        return request.client.host if request.client else "unknown"

    @staticmethod
    def normalize(value: str | None) -> str:
        return (value or "").strip().lower()


class RedisRateLimiter:
    """Rate limiter distribuido para despliegues con varias instancias."""

    _SCRIPT = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window_start = now - tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local member = ARGV[4]

    redis.call("ZREMRANGEBYSCORE", key, 0, window_start)
    local count = redis.call("ZCARD", key)
    if count >= limit then
        local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")[2]
        return {0, oldest}
    end

    redis.call("ZADD", key, now, member)
    redis.call("EXPIRE", key, tonumber(ARGV[2]))
    return {1, 0}
    """

    def __init__(self, redis_url: str):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "El backend Redis del rate limiter requiere instalar la dependencia redis."
            ) from exc

        self._redis_error = redis.exceptions.RedisError
        self._client = redis.Redis.from_url(redis_url, decode_responses=False)
        self._script = self._client.register_script(self._SCRIPT)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time()
        redis_key = f"usersapi:rate-limit:{key}"
        member = f"{now}:{uuid4().hex}"
        try:
            allowed, oldest = self._script(
                keys=[redis_key],
                args=[now, window_seconds, limit, member],
            )
        except self._redis_error as exc:
            raise RuntimeError("No fue posible consultar Redis para el rate limiter.") from exc

        if int(allowed) == 0:
            retry_after = max(1, int(float(oldest) + window_seconds - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Inténtalo nuevamente más tarde.",
                headers={"Retry-After": str(retry_after)},
            )

    def reset(self) -> None:
        """Elimina las claves del limiter; usado para aislar pruebas."""
        try:
            keys = list(self._client.scan_iter(match="usersapi:rate-limit:*"))
            if keys:
                self._client.delete(*keys)
        except self._redis_error as exc:
            raise RuntimeError("No fue posible limpiar las claves Redis del rate limiter.") from exc

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def status(self) -> dict[str, object]:
        return {"backend": "redis", "connected": self.ping()}

    @staticmethod
    def client_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    @staticmethod
    def normalize(value: str | None) -> str:
        return (value or "").strip().lower()


def _build_rate_limiter():
    backend = settings.rate_limit_backend
    if APP_ENV == "production" and backend != "redis":
        raise RuntimeError("En producción RATE_LIMIT_BACKEND debe ser 'redis'.")
    if backend == "redis":
        if not settings.redis_url:
            raise RuntimeError("REDIS_URL es obligatoria cuando RATE_LIMIT_BACKEND=redis.")
        return RedisRateLimiter(settings.redis_url)
    if backend != "memory":
        raise RuntimeError("RATE_LIMIT_BACKEND debe ser 'memory' o 'redis'.")
    return InMemoryRateLimiter()


rate_limiter = _build_rate_limiter()

if settings.rate_limit_backend == "redis":
    if rate_limiter.ping():
        logger.info("Rate limiter conectado a Redis exitosamente.")
    else:
        logger.warning(
            "Rate limiter configurado para Redis, pero no se pudo verificar la conexión inicial."
        )
else:
    logger.debug("Rate limiter inicializado en memoria (InMemoryRateLimiter).")


LOGIN_IP_LIMIT = 30
LOGIN_IP_WINDOW = 10 * 60
LOGIN_ACCOUNT_LIMIT = 5
LOGIN_ACCOUNT_WINDOW = 10 * 60

SUPER_LOGIN_LIMIT = 5
SUPER_LOGIN_WINDOW = 15 * 60
SUPER_MFA_LIMIT = 5
SUPER_MFA_WINDOW = 10 * 60

PASSWORD_RECOVERY_REQUEST_LIMIT = 5
PASSWORD_RECOVERY_REQUEST_WINDOW = 15 * 60
PASSWORD_RECOVERY_RESET_LIMIT = 5
PASSWORD_RECOVERY_RESET_WINDOW = 10 * 60

OTP_GENERATE_LIMIT = 5
OTP_GENERATE_WINDOW = 15 * 60
OTP_VALIDATE_LIMIT = 5
OTP_VALIDATE_WINDOW = 10 * 60

SUPER_BOOTSTRAP_LIMIT = 5
SUPER_BOOTSTRAP_WINDOW = 15 * 60

TENANT_BOOTSTRAP_LIMIT = 5
TENANT_BOOTSTRAP_WINDOW = 15 * 60

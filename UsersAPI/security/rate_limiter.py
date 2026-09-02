from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


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


rate_limiter = InMemoryRateLimiter()


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

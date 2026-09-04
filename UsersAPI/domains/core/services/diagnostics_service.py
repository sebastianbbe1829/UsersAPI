from fastapi import Request

from ..logging_config import logger


def get_client_ip_diagnostic(request: Request) -> dict[str, str]:
    """Returns the client IP observed by FastAPI behind the deployment proxy."""
    client_host = request.client.host if request.client else "unknown"

    logger.warning(
        "Rate limiter IP diagnostic requested: client_host=%s",
        client_host,
    )

    return {
        "status": "enabled",
        "client_host": client_host,
    }

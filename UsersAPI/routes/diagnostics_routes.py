import os

from fastapi import APIRouter, Request

from ..logging_config import logger

router = APIRouter(prefix="/diagnostics", tags=["Diagnóstico"])


@router.get("/client-ip", include_in_schema=False)
def client_ip_diagnostic(request: Request):
    """Temporary production diagnostic for proxy/client-IP verification.

    Enabled only when RATE_LIMITER_IP_DIAGNOSTIC is explicitly true.
    It reports only connection/proxy metadata and never authentication data.
    """
    if os.getenv("RATE_LIMITER_IP_DIAGNOSTIC", "false").lower() != "true":
        return {"status": "disabled"}

    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")

    logger.warning(
        "Rate limiter IP diagnostic: client_host=%s x_forwarded_for=%s x_real_ip=%s",
        client_host,
        forwarded_for or "<absent>",
        real_ip or "<absent>",
    )

    return {
        "status": "enabled",
        "client_host": client_host,
        "x_forwarded_for": forwarded_for,
        "x_real_ip": real_ip,
    }

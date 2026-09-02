from fastapi import HTTPException, Request, status

from ..models import GlobalUserDB
from ..services.diagnostics_service import get_client_ip_diagnostic as get_client_ip_diagnostic_service


def get_client_ip_diagnostic(
    request: Request,
    current_user: object,
) -> dict[str, str]:
    """Authorizes and delegates the client-IP diagnostic to the service layer."""
    if not isinstance(current_user, GlobalUserDB):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere una sesión SUPER",
        )

    return get_client_ip_diagnostic_service(request)

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..controllers.auth_controller import get_current_user
from ..logging_config import logger
from ..models import GlobalUserDB, UserTenantDB

router = APIRouter(prefix="/diagnostics", tags=["Diagnóstico"])


def require_super_user(
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
) -> GlobalUserDB:
    """Permite diagnósticos de infraestructura únicamente a usuarios SUPER."""
    if not isinstance(current_user, GlobalUserDB):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere una sesión SUPER",
        )

    return current_user


@router.get("/client-ip", include_in_schema=False)
def client_ip_diagnostic(
    request: Request,
    _current_user: GlobalUserDB = Depends(require_super_user),
):
    """Diagnóstico operativo de la IP observada por FastAPI detrás de Render."""
    client_host = request.client.host if request.client else "unknown"

    logger.warning(
        "Rate limiter IP diagnostic requested: client_host=%s",
        client_host,
    )

    return {
        "status": "enabled",
        "client_host": client_host,
    }

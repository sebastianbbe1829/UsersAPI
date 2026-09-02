from fastapi import APIRouter, Depends, Request

from ..controllers.diagnostics_controller import get_client_ip_diagnostic
from ..controllers.auth_controller import get_current_user
from ..models import GlobalUserDB, UserTenantDB

router = APIRouter(prefix="/diagnostics", tags=["Diagnóstico"])


@router.get("/client-ip", include_in_schema=False)
def client_ip_diagnostic(
    request: Request,
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_user),
):
    return get_client_ip_diagnostic(request, current_user)

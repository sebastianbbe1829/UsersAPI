from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..controllers.diagnostics_controller import get_client_ip_diagnostic
from ..database import get_db
from ..models import GlobalUserDB, UserTenantDB
from ..security.dependencies import get_current_tenant

router = APIRouter(prefix="/diagnostics", tags=["Diagnóstico"])


@router.get("/client-ip", include_in_schema=False)
def client_ip_diagnostic(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserTenantDB | GlobalUserDB = Depends(get_current_tenant),
):
    return get_client_ip_diagnostic(request, db, current_user)

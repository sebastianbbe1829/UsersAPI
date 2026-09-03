import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..controllers.bootstrap_tenant_controller import bootstrap_tenant_application
from ..database import get_bootstrap_db
from ..schemas import BootstrapTenantRequest, BootstrapTenantResponse
from ..settings import settings


bootstrap_tenant_routes = APIRouter(
    prefix="/bootstrap",
    tags=["Bootstrap"],
)


@bootstrap_tenant_routes.post(
    "",
    response_model=BootstrapTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_route(
    datos: BootstrapTenantRequest,
    x_bootstrap_key: str | None = Header(None, alias="X-Bootstrap-Key"),
    x_bootstrap_tenant_key: str | None = Header(
        None,
        alias="X-Bootstrap-Tenant-Key",
    ),
    db: Session = Depends(get_bootstrap_db),
):
    """Provisiona una nueva empresa mediante una clave interna.

    Se mantienen ambos nombres de header para compatibilidad con clientes
    existentes: X-Bootstrap-Key y X-Bootstrap-Tenant-Key.
    """
    bootstrap_key = x_bootstrap_key or x_bootstrap_tenant_key

    if bootstrap_key is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Falta la clave de bootstrap.",
        )

    if not settings.bootstrap_tenant_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BOOTSTRAP_TENANT_KEY no está configurada.",
        )

    if not secrets.compare_digest(
        bootstrap_key,
        settings.bootstrap_tenant_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de bootstrap inválida.",
        )

    return bootstrap_tenant_application(
        datos=datos,
        db=db,
    )


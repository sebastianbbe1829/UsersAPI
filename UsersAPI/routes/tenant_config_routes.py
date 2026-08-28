from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..controllers.auth_controller import get_current_user
from ..controllers.tenant_config_controller import (
    actualizar_config_tenant,
    obtener_config_tenant,
)
from ..database import get_db
from ..models import TenantDB, UserTenantDB
from ..schemas import TenantConfigRead, TenantConfigUpdate
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


tenant_config_routes = APIRouter(
    prefix="/tenant-config",
    tags=["Configuración UI"],
)


@tenant_config_routes.get(
    "",
    response_model=TenantConfigRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener configuración visual del tenant actual",
    dependencies=[Depends(require_permission("TENANT_READ"))],
)
async def obtener_config_tenant_route(
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    tenant = user_tenant.tenant
    return obtener_config_tenant(
        tenant=tenant,
        db=db,
        current_user=user_tenant,
    )


@tenant_config_routes.patch(
    "",
    response_model=TenantConfigRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar configuración visual del tenant actual",
    dependencies=[Depends(require_permission("TENANT_UPDATE"))],
)
async def actualizar_config_tenant_route(
    datos: TenantConfigUpdate,
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    current_user: UserTenantDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = user_tenant.tenant
    return actualizar_config_tenant(
        tenant=tenant,
        datos=datos,
        db=db,
        current_user=current_user,
    )

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..controllers.auth_controller import get_current_user
from ..controllers.tenant_config_controller import (
    actualizar_config_tenant,
    obtener_config_tenant,
)
from ..database import get_bootstrap_db, get_db
from ..models import GlobalUserDB, UserTenantDB
from ..repositories.tenant_repository import TenantRepository
from ..schemas import TenantConfigRead, TenantConfigUpdate
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission
from ..services.super_mfa_service import verify_super_mfa_otp
from ..services.super_tenant_service import require_super_user


tenant_config_routes = APIRouter(
    prefix="/tenant-config",
    tags=["Configuración UI"],
)


@tenant_config_routes.get(
    "",
    response_model=TenantConfigRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener configuración visual del tenant actual",
    dependencies=[Depends(require_permission("CONFIG_UI_READ"))],
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
    dependencies=[Depends(require_permission("CONFIG_UI_UPDATE"))],
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


@tenant_config_routes.get(
    "/admin/{tenant_id}",
    response_model=TenantConfigRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener configuración visual de cualquier tenant como SUPER",
)
async def obtener_config_tenant_super_route(
    tenant_id: int = Path(..., description="ID del tenant"),
    db: Session = Depends(get_bootstrap_db),
    current_user: GlobalUserDB = Depends(get_current_user),
):
    super_user = require_super_user(current_user)

    tenant = TenantRepository(db).get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado.",
        )

    return obtener_config_tenant(
        tenant=tenant,
        db=db,
        current_user=super_user,
    )


@tenant_config_routes.patch(
    "/admin/{tenant_id}",
    response_model=TenantConfigRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar configuración visual de cualquier tenant como SUPER",
)
async def actualizar_config_tenant_super_route(
    tenant_id: int,
    datos: TenantConfigUpdate,
    x_super_mfa_otp: str = Header(..., alias="X-Super-MFA-OTP"),
    db: Session = Depends(get_bootstrap_db),
    current_user: GlobalUserDB = Depends(get_current_user),
):
    super_user = require_super_user(current_user)
    verify_super_mfa_otp(super_user, x_super_mfa_otp)

    tenant = TenantRepository(db).get_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado.",
        )

    return actualizar_config_tenant(
        tenant=tenant,
        datos=datos,
        db=db,
        current_user=super_user,
    )

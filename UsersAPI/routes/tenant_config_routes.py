from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.orm import Session

from ..controllers.auth_controller import get_current_user
from ..controllers.tenant_config_controller import (
    actualizar_config_tenant,
    obtener_config_tenant,
)
from ..database import get_bootstrap_db
from ..models import GlobalUserDB
from ..schemas import TenantConfigRead, TenantConfigUpdate
from ..services.super_tenant_service import require_super_user
from ..services.super_mfa_service import verify_super_mfa_otp
from ..repositories.tenant_repository import TenantRepository


tenant_config_routes = APIRouter(
    prefix="/tenant-config",
    tags=["Configuración UI"],
)


# ============================================================
# ADMINISTRACIÓN DE CONFIGURACIÓN UI - SUPER
#
# Estas rutas son administrativas y siguen el mismo modelo que
# la administración global de tenants: sesión SUPER y acceso
# mediante BOOTSTRAP_DATABASE_URL (BYPASSRLS).
# ============================================================


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
        from fastapi import HTTPException
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
        from fastapi import HTTPException
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

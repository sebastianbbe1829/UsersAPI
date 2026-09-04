from typing import List, cast

from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.orm import Session

from ..controllers import (
    crear_tenant,
    listar_tenants,
    listar_mis_tenants,
    obtener_tenant,
    actualizar_tenant,
    eliminar_tenant,
    get_current_user,
)
from ..controllers import super_tenant_controller
from ..database import get_db, get_bootstrap_db
from ..models import UserTenantDB
from ..schemas import (
    BootstrapTenantRequest,
    BootstrapTenantResponse,
    TenantCreate,
    TenantDeleteResponse,
    TenantRead,
    TenantUpdate,
)
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


tenant_routes = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
)


# ============================================================
# ADMINISTRACIÓN GLOBAL DE TENANTS - SUPER
#
# Estas rutas no utilizan el contexto RLS del tenant del JWT.
# La sesión SUPER se valida con DATABASE_URL y las operaciones
# sobre tenants se ejecutan mediante BOOTSTRAP_DATABASE_URL,
# cuyo usuario tiene BYPASSRLS.
# ============================================================

@tenant_routes.get(
    "/admin",
    response_model=List[TenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar todos los tenants como SUPER",
)
async def listar_tenants_super_route(
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return super_tenant_controller.listar_tenants_super(
        db=db,
        current_user=current_user,
    )


@tenant_routes.get(
    "/admin/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener cualquier tenant como SUPER",
)
async def obtener_tenant_super_route(
    tenant_id: int = Path(..., description="ID del tenant"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return super_tenant_controller.obtener_tenant_super(
        tenant_id=tenant_id,
        db=db,
        current_user=current_user,
    )


@tenant_routes.post(
    "/admin/provision",
    response_model=BootstrapTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provisionar un nuevo tenant como SUPER",
)
async def crear_tenant_super_route(
    datos: BootstrapTenantRequest,
    x_super_mfa_otp: str = Header(..., alias="X-Super-MFA-OTP"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return super_tenant_controller.crear_tenant_super(
        datos=datos,
        otp=x_super_mfa_otp,
        db=db,
        current_user=current_user,
    )


@tenant_routes.patch(
    "/admin/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar cualquier tenant como SUPER",
)
async def actualizar_tenant_super_route(
    tenant_id: int,
    datos: TenantUpdate,
    x_super_mfa_otp: str = Header(..., alias="X-Super-MFA-OTP"),
    db: Session = Depends(get_bootstrap_db),
    current_user=Depends(get_current_user),
):
    return super_tenant_controller.actualizar_tenant_super(
        tenant_id=tenant_id,
        datos=datos,
        otp=x_super_mfa_otp,
        db=db,
        current_user=current_user,
    )


# ============================================================
# CREAR TENANT
# ============================================================

@tenant_routes.post(
    "",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tenant",
    dependencies=[
        Depends(require_permission("TENANT_CREATE")),
    ],
)
async def crear_tenant_route(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
):
    return crear_tenant(
        tenant,
        db,
        current_user,
    )


# ============================================================
# LISTAR TENANTS
# ============================================================

@tenant_routes.get(
    "",
    response_model=List[TenantRead],
    status_code=status.HTTP_200_OK,
    summary="Obtener tenant actual",
    dependencies=[
        Depends(require_permission("TENANT_READ")),
    ],
)
async def listar_tenants_route(
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return listar_tenants(
        tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# LISTAR MIS TENANTS
# ============================================================

@tenant_routes.get(
    "/my",
    response_model=List[TenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar mis tenants",
    dependencies=[
        Depends(require_permission("TENANT_READ")),
    ],
)
async def listar_mis_tenants_route(
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
):
    return listar_mis_tenants(
        db=db,
        current_user=current_user,
    )


# ============================================================
# OBTENER TENANT
# ============================================================

@tenant_routes.get(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener tenant por ID",
    dependencies=[
        Depends(require_permission("TENANT_READ")),
    ],
)
async def obtener_tenant_route(
    tenant_id: int = Path(
        ...,
        description="ID del tenant",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return obtener_tenant(
        tenant_id=tenant_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )


# ============================================================
# ACTUALIZAR TENANT
# ============================================================

@tenant_routes.patch(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar tenant",
    dependencies=[
        Depends(require_permission("TENANT_UPDATE")),
    ],
)
async def actualizar_tenant_route(
    tenant_id: int,
    datos: TenantUpdate,
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    current_user: UserTenantDB = Depends(get_current_user),
):
    return actualizar_tenant(
        tenant_id=tenant_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        datos=datos,
        db=db,
        current_user=current_user,
    )


# ============================================================
# ELIMINAR TENANT
# ============================================================

@tenant_routes.delete(
    "/{tenant_id}",
    response_model=TenantDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar tenant",
    dependencies=[
        Depends(require_permission("TENANT_DELETE")),
    ],
)
async def eliminar_tenant_route(
    tenant_id: int = Path(
        ...,
        description="ID del tenant",
    ),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return eliminar_tenant(
        tenant_id=tenant_id,
        current_tenant_id=cast(int, user_tenant.tenant_id),
        db=db,
    )

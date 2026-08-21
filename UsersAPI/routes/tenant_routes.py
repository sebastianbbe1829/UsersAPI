from typing import List

from fastapi import APIRouter, Depends, Path, Query, status

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

from ..database import get_db

from ..models import UserDB

from ..schemas import (
    TenantCreate,
    TenantDeleteResponse,
    TenantRead,
    TenantUpdate,
)

from ..security.permissions import require_permission


tenant_routes = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
)


# ============================================================
# CREAR TENANT
#
# POST /tenants
#
# Permiso requerido:
#   TENANT_CREATE
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
    current_user: UserDB = Depends(get_current_user),
):

    return crear_tenant(
        tenant,
        db,
        current_user,
    )


# ============================================================
# LISTAR TENANTS
#
# GET /tenants
#
# Permiso requerido:
#   TENANT_READ
# ============================================================

@tenant_routes.get(
    "",
    response_model=List[TenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar tenants",
    dependencies=[
        Depends(require_permission("TENANT_READ")),
    ],
)
async def listar_tenants_route(
    status: int | None = Query(
        None,
        description="Filtra tenants por estado (0=inactivo, 1=activo)",
    ),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return listar_tenants(
        db,
        status,
    )


# ============================================================
# LISTAR MIS TENANTS
#
# GET /tenants/my
#
# Permiso requerido:
#   TENANT_READ
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
    current_user: UserDB = Depends(get_current_user),
):

    return listar_mis_tenants(
        db=db,
        current_user=current_user,
    )


# ============================================================
# OBTENER TENANT
#
# GET /tenants/{tenant_id}
#
# Permiso requerido:
#   TENANT_READ
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
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return obtener_tenant(
        tenant_id,
        db,
    )


# ============================================================
# ACTUALIZAR TENANT
#
# PATCH /tenants/{tenant_id}
#
# Permiso requerido:
#   TENANT_UPDATE
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
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return actualizar_tenant(
        tenant_id,
        datos,
        db,
        current_user,
    )


# ============================================================
# ELIMINAR TENANT
#
# DELETE /tenants/{tenant_id}
#
# Permiso requerido:
#   TENANT_DELETE
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
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    return eliminar_tenant(
        tenant_id,
        db,
    )
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

tenant_routes = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
)


@tenant_routes.post(
    "",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tenant",
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


@tenant_routes.get(
    "",
    response_model=List[TenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar tenants",
)
async def listar_tenants_route(
    status: int
    | None = Query(
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

@tenant_routes.get(
    "/my",
    response_model=List[TenantRead],
    status_code=status.HTTP_200_OK,
    summary="Listar mis tenants",
)
async def listar_mis_tenants_route(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return listar_mis_tenants(
        db=db,
        current_user=current_user,
    )

@tenant_routes.get(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener tenant por ID",
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


@tenant_routes.patch(
    "/{tenant_id}",
    response_model=TenantRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar tenant",
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


@tenant_routes.delete(
    "/{tenant_id}",
    response_model=TenantDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Eliminar tenant",
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

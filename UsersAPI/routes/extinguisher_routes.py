from typing import cast

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from ..controllers import extinguisher_controller
from ..database import get_db
from ..models import UserTenantDB
from ..schemas import (
    ExtinguisherCreate,
    ExtinguisherDeleteResponse,
    ExtinguisherRead,
    ExtinguisherUpdate,
)
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


extinguisher_routes = APIRouter(
    prefix="/extinguishers",
    tags=["Extintores"],
)


@extinguisher_routes.post(
    "",
    response_model=ExtinguisherRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_CREATE"))],
)
async def crear_extintor(
    datos: ExtinguisherCreate,
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_controller.crear_extintor(datos, db, user_tenant)


@extinguisher_routes.get(
    "",
    response_model=list[ExtinguisherRead],
    status_code=status.HTTP_200_OK,
    summary="Listar extintores",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def listar_extintores(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_controller.listar_extintores(
        db,
        cast(int, user_tenant.tenant_id),
        include_inactive,
    )


@extinguisher_routes.get(
    "/{extinguisher_id}",
    response_model=ExtinguisherRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def obtener_extintor(
    extinguisher_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_controller.obtener_extintor(
        extinguisher_id,
        db,
        cast(int, user_tenant.tenant_id),
    )


@extinguisher_routes.patch(
    "/{extinguisher_id}",
    response_model=ExtinguisherRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_UPDATE"))],
)
async def actualizar_extintor(
    datos: ExtinguisherUpdate,
    extinguisher_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_controller.actualizar_extintor(
        extinguisher_id,
        datos,
        db,
        user_tenant,
    )


@extinguisher_routes.delete(
    "/{extinguisher_id}",
    response_model=ExtinguisherDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Desactivar extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_DELETE"))],
)
async def eliminar_extintor(
    extinguisher_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_controller.eliminar_extintor(
        extinguisher_id,
        db,
        user_tenant,
    )

from typing import cast

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from ..controllers import extinguisher_inspection_controller
from ..database import get_db
from ..models import UserTenantDB
from ..schemas.extinguisher_inspection import (
    ExtinguisherInspectionCreate,
    ExtinguisherInspectionItemRead,
    ExtinguisherInspectionRead,
)
from ..security.dependencies import get_current_tenant
from ..security.permissions import require_permission


extinguisher_inspection_routes = APIRouter(
    prefix="/extinguisher-inspections",
    tags=["Revisiones de extintores"],
)


@extinguisher_inspection_routes.get(
    "/items",
    response_model=list[ExtinguisherInspectionItemRead],
    status_code=status.HTTP_200_OK,
    summary="Listar ítems de revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def listar_items_revision(db: Session = Depends(get_db)):
    return extinguisher_inspection_controller.listar_items_revision(db)


@extinguisher_inspection_routes.get(
    "",
    response_model=list[ExtinguisherInspectionRead],
    status_code=status.HTTP_200_OK,
    summary="Listar revisiones",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def listar_revisiones(
    extinguisher_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_inspection_controller.listar_revisiones(
        db, cast(int, user_tenant.tenant_id), extinguisher_id
    )


@extinguisher_inspection_routes.get(
    "/{inspection_id}",
    response_model=ExtinguisherInspectionRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def obtener_revision(
    inspection_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_inspection_controller.obtener_revision(
        inspection_id, db, cast(int, user_tenant.tenant_id)
    )


@extinguisher_inspection_routes.post(
    "/extinguishers/{extinguisher_id}",
    response_model=ExtinguisherInspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear revisión de extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_UPDATE"))],
)
async def crear_revision(
    datos: ExtinguisherInspectionCreate,
    extinguisher_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    user_tenant: UserTenantDB = Depends(get_current_tenant),
):
    return extinguisher_inspection_controller.crear_revision(
        extinguisher_id, datos, db, user_tenant
    )

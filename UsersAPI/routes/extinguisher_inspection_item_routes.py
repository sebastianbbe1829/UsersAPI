from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from ..controllers import extinguisher_inspection_item_controller
from ..database import get_db
from ..schemas.extinguisher_inspection_item import (
    ExtinguisherInspectionItemCreate,
    ExtinguisherInspectionItemRead,
    ExtinguisherInspectionItemUpdate,
)
from ..security.permissions import require_permission


extinguisher_inspection_item_routes = APIRouter(
    prefix="/extinguisher-inspection-items",
    tags=["Ítems de revisión"],
)


@extinguisher_inspection_item_routes.get(
    "",
    response_model=list[ExtinguisherInspectionItemRead],
    status_code=status.HTTP_200_OK,
    summary="Listar ítems de revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def listar_items_revision(db: Session = Depends(get_db)):
    return extinguisher_inspection_item_controller.listar_items_revision(db)


@extinguisher_inspection_item_routes.get(
    "/{item_id}",
    response_model=ExtinguisherInspectionItemRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener ítem de revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def obtener_item_revision(
    item_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    return extinguisher_inspection_item_controller.obtener_item_revision(item_id, db)


@extinguisher_inspection_item_routes.post(
    "",
    response_model=ExtinguisherInspectionItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear ítem de revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_UPDATE"))],
)
async def crear_item_revision(
    datos: ExtinguisherInspectionItemCreate,
    db: Session = Depends(get_db),
):
    return extinguisher_inspection_item_controller.crear_item_revision(datos, db)


@extinguisher_inspection_item_routes.put(
    "/{item_id}",
    response_model=ExtinguisherInspectionItemRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar ítem de revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_UPDATE"))],
)
async def actualizar_item_revision(
    datos: ExtinguisherInspectionItemUpdate,
    item_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    return extinguisher_inspection_item_controller.actualizar_item_revision(item_id, datos, db)


@extinguisher_inspection_item_routes.delete(
    "/{item_id}",
    response_model=ExtinguisherInspectionItemRead,
    status_code=status.HTTP_200_OK,
    summary="Desactivar ítem de revisión",
    dependencies=[Depends(require_permission("EXTINGUISHER_UPDATE"))],
)
async def desactivar_item_revision(
    item_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    return extinguisher_inspection_item_controller.desactivar_item_revision(item_id, db)

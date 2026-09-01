from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..controllers import extinguisher_type_controller
from ..database import get_db
from ..schemas import ExtinguisherTypeCreate, ExtinguisherTypeRead
from ..security.permissions import require_permission


extinguisher_type_routes = APIRouter(
    prefix="/extinguisher-types",
    tags=["Tipos de extintor"],
)


@extinguisher_type_routes.get(
    "",
    response_model=list[ExtinguisherTypeRead],
    status_code=status.HTTP_200_OK,
    summary="Listar tipos de extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_READ"))],
)
async def listar_tipos_extintor(db: Session = Depends(get_db)):
    return extinguisher_type_controller.listar_tipos_extintor(db)


@extinguisher_type_routes.post(
    "",
    response_model=ExtinguisherTypeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tipo de extintor",
    dependencies=[Depends(require_permission("EXTINGUISHER_CREATE"))],
)
async def crear_tipo_extintor(datos: ExtinguisherTypeCreate, db: Session = Depends(get_db)):
    return extinguisher_type_controller.crear_tipo_extintor(datos, db)

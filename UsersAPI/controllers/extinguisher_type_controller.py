from sqlalchemy.orm import Session

from ..schemas import ExtinguisherTypeCreate, ExtinguisherTypeUpdate
from ..services.extinguisher_type_service import (
    create_extinguisher_type,
    delete_extinguisher_type,
    list_extinguisher_types,
    update_extinguisher_type,
)


def listar_tipos_extintor(db: Session):
    return list_extinguisher_types(db)


def crear_tipo_extintor(datos: ExtinguisherTypeCreate, db: Session):
    return create_extinguisher_type(datos, db)


def actualizar_tipo_extintor(type_id: int, datos: ExtinguisherTypeUpdate, db: Session):
    return update_extinguisher_type(type_id, datos, db)


def eliminar_tipo_extintor(type_id: int, db: Session):
    return delete_extinguisher_type(type_id, db)
